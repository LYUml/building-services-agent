"""Derive pressure-network geometry from explicit IFC-envelope port chains."""
import argparse
import copy
import json
import math
from pathlib import Path
from .engine import ProjectError
from .cli import digest


def prepare(network, model, binding):
    from .bim import validate as validate_bim
    from .network import validate as validate_network
    validate_bim(model)
    if not isinstance(binding, dict) or set(binding) != {'source', 'nodes', 'segments'}:
        raise ProjectError('binding requires source, node ports and segment device chains')
    if not isinstance(binding['source'], str) or not binding['source'].strip():
        raise ProjectError('binding provenance required')
    result = copy.deepcopy(network)
    devices = {d['id']: d for d in model['devices']}
    ports = {}
    for d in devices.values():
        for port in d.get('ports', []):
            ports[d['id'] + '.' + port['id']] = (d, port, [a+b for a,b in zip(d['origin_m'],port['offset_m'])])
    def point(ref):
        if not isinstance(ref,str) or ref not in ports: raise ProjectError('unknown bound port')
        return ports[ref][2]
    def same(a,b): return all(abs(x-y)<=1e-8 for x,y in zip(a,b))
    if not isinstance(binding['nodes'],dict) or not isinstance(binding['segments'],dict):
        raise ProjectError('binding maps required')
    if set(binding['nodes']) != {n['id'] for n in result['nodes']} or set(binding['segments']) != {s['id'] for s in result['segments']}:
        raise ProjectError('exact node and segment binding coverage required')
    for n in result['nodes']:
        if 'elevation_m' in n: raise ProjectError('network must not repeat bound elevation')
        n['elevation_m'] = point(binding['nodes'][n['id']])[2]
    links = {(c['from'], c['to']) for c in model['connections']}
    used = set(); evidence = []
    for s in result['segments']:
        if 'length_m' in s or 'diameter_m' in s: raise ProjectError('network must not repeat bound length or diameter')
        chain = binding['segments'][s['id']]
        if not isinstance(chain,list) or not chain: raise ProjectError('nonempty ordered segment device chain required')
        lengths=[]; diameters=[]; previous=None; start=None; end=None; system=None; route_class=None; first_port=None
        for identifier in chain:
            if not isinstance(identifier,str) or identifier not in devices or identifier in used:
                raise ProjectError('unique known route devices required')
            used.add(identifier); d=devices[identifier]
            if d['ifc_class'] not in ('IfcDuctSegment','IfcPipeSegment'): raise ProjectError('route must use duct or pipe segments')
            if route_class is None: route_class=d['ifc_class']
            if route_class!=d['ifc_class']:raise ProjectError('route mixes pipe and duct classes')
            if system is None: system=d['system']
            if d['system'] != system: raise ProjectError('route changes distribution system')
            ps=d.get('ports',[])
            incoming=[p for p in ps if p['direction']=='SINK']; outgoing=[p for p in ps if p['direction']=='SOURCE']
            if len(ps)!=2 or len(incoming)!=1 or len(outgoing)!=1: raise ProjectError('each route piece requires one inlet and one outlet')
            inlet=identifier+'.'+incoming[0]['id']; outlet=identifier+'.'+outgoing[0]['id']
            a,b=point(inlet),point(outlet)
            axes=[i for i in range(3) if abs(a[i]-b[i])>1e-8]
            if len(axes)!=1: raise ProjectError('only straight axis-aligned port-centre routes supported')
            axis=axes[0]
            # Opposite end-face centres prevent a box diagonal or arbitrary offset becoming route length.
            for xyz in (a,b):
                for i in range(3):
                    if i!=axis and abs(xyz[i]-(d['origin_m'][i]+d['size_m'][i]/2))>1e-8:
                        raise ProjectError('route ports must be end-face centres')
            if abs(min(a[axis],b[axis])-d['origin_m'][axis])>1e-8 or abs(max(a[axis],b[axis])-(d['origin_m'][axis]+d['size_m'][axis]))>1e-8:
                raise ProjectError('route ports must span the full envelope axis')
            diameter=d.get('properties',{}).get('InternalDiameter_m')
            if type(diameter) not in (int,float) or not math.isfinite(diameter) or diameter<=0:
                raise ProjectError('explicit source-backed internal diameter property required')
            if any(diameter>d['size_m'][i]+1e-8 for i in range(3) if i!=axis):
                raise ProjectError('internal diameter exceeds transverse envelope')
            if previous and ((previous,inlet) not in links or not same(point(previous),a)):
                raise ProjectError('route pieces require connected coincident ports')
            if start is None: start=a;first_port=inlet
            end=b; previous=outlet; lengths.append(abs(b[axis]-a[axis])); diameters.append(diameter)
        if any(abs(v-diameters[0])>1e-10 for v in diameters): raise ProjectError('split hydraulic segments where internal diameter changes')
        if not same(start,point(binding['nodes'][s['from']])) or not same(end,point(binding['nodes'][s['to']])):
            raise ProjectError('network endpoints differ from bound model node coordinates')
        for node_ref,route_ref,is_start in ((binding['nodes'][s['from']],first_port,True),(binding['nodes'][s['to']],previous,False)):
            node_device=ports[node_ref][0]
            if node_device['system']!=system:raise ProjectError('bound node changes distribution system')
            # A junction may have multiple coincident ports; all must belong to the bound node device.
            candidates=[ref for ref,(device,port,xyz) in ports.items()
                        if device['id']==node_device['id'] and same(xyz,point(node_ref))]
            if node_ref!=route_ref and not any((ref,route_ref) in links if is_start else (route_ref,ref) in links for ref in candidates):
                raise ProjectError('bound node requires a coincident model connection to route')
        s['length_m']=sum(lengths); s['diameter_m']=diameters[0]
        evidence.append(dict(id=s['id'],devices=chain,length_m=s['length_m'],diameter_m=s['diameter_m']))
    validate_network(result)
    return result,evidence


def reconcile(model_path, derived_path, binding):
    """Read saved IFC port positions/diameters, rather than trusting generated JSON."""
    import ifcopenshell
    import ifcopenshell.util.element as element
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    import ifcopenshell.util.unit as unit
    model=ifcopenshell.open(str(model_path))
    if not math.isclose(unit.calculate_unit_scale(model),1):raise ProjectError('bound IFC metre units required')
    derived=json.loads(Path(derived_path).read_text(encoding='utf-8-sig'))
    devices={d.Name:d for d in model.by_type('IfcDistributionElement')}
    ports={}
    for d in devices.values():
        for p in system.get_ports(d):
            ports[d.Name+'.'+p.Name]=(p,placement.get_local_placement(p.ObjectPlacement)[:3,3])
    for n in derived['nodes']:
        if abs(ports[binding['nodes'][n['id']]][1][2]-n['elevation_m'])>1e-8:
            raise ProjectError('saved IFC/network elevation mismatch')
    for s in derived['segments']:
        length=0;first=None;last=None
        for identifier in binding['segments'][s['id']]:
            obj=devices[identifier]
            ps=[value for key,value in ports.items() if system.get_port_element(value[0])==obj]
            inlet=next(xyz for p,xyz in ps if p.FlowDirection=='SINK')
            outlet=next(xyz for p,xyz in ps if p.FlowDirection=='SOURCE')
            length+=math.dist(inlet,outlet)
            if first is None:first=inlet
            last=outlet
            diameter=element.get_psets(obj)['BSA_DesignInputs'].get('InternalDiameter_m')
            if type(diameter) not in (int,float) or not math.isclose(diameter,s['diameter_m'],rel_tol=0,abs_tol=1e-10):
                raise ProjectError('saved IFC/network internal diameter mismatch')
        if not math.isclose(length,s['length_m'],rel_tol=0,abs_tol=1e-8):raise ProjectError('saved IFC/network route length mismatch')
        for xyz,node in ((first,s['from']),(last,s['to'])):
            if math.dist(xyz,ports[binding['nodes'][node]][1])>1e-8:raise ProjectError('saved IFC/network endpoint mismatch')
    return True


def run(network,model,binding,out):
    from .bim import run as author
    from .network import run as analyse
    paths=[Path(p).resolve() for p in (network,model,binding)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain sources')
    before={str(p):digest(p) for p in paths}
    data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    derived,evidence=prepare(*data)
    out.mkdir(parents=True,exist_ok=False)
    generated=out/'network-input.json';generated.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    author(paths[1],out/'bim');calculation=analyse(generated,out/'analysis')
    saved_match=reconcile(out/'bim/model.ifc',generated,data[2])
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('bound source changed')
    result=dict(inputs=before,inputs_unchanged=True,binding_source=data[2]['source'],segments=evidence,
        saved_ifc_geometry_match=saved_match,calculated_checks_pass=saved_match and calculation['calculated_checks_pass'],design_accepted=False,
        scope='Straight axis-aligned circular port-centre routes; derived length/elevation/internal diameter, reopened IFC geometry and pressure budget',
        pending=['junction and fitting physical detail','K reference and circular-section evidence','routing/clash and full engineering acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'network-binding.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('network',type=Path)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(a.network,a.model,a.binding,a.out)
    print(json.dumps({'calculated_checks_pass':r['calculated_checks_pass'],'design_accepted':False}))
    return 0 if r['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())
