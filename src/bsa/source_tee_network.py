"""Trim verified source straights and append verified local tee candidates to a fresh IFC."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import numpy as np
from . import source_tee_candidates as candidates, duct_elbow_backbone as backbone
from . import rectangular_geometry as straight, bim, duct_fitting_chain as chain
from .rectangular_tee_transitions import relative_placement
from .cli import digest
from .workspace import allowed


def compile_model(original, junction, selected, rows, blocked):
    """Apply only actually authored tees; retain all other source obligations."""
    model=copy.deepcopy(original); devices={d['id']:d for d in model['devices']}
    incidents={n['node']:n for n in junction['nodes']}; trims={}; interfaces=[]
    for name,row in rows.items():
        if name in blocked: continue
        for arm in row['fit']['arms']:
            sid=arm['section']; incident=next(i for i in incidents[name]['incidents'] if i['section']==sid)
            port='out' if incident['role']=='incoming' else 'in'
            key=(sid,port)
            if key in trims: raise ValueError('Duplicate source endpoint consumption')
            trims[key]=arm['outward_reach_m']
            interfaces.append(dict(node=name,arm=arm['arm'],section=sid,port=port,
                width_m=arm['width_m'],height_m=arm['height_m'],reach_m=arm['outward_reach_m']))
    budgets=[]; minimum=selected['policy']['minimum_remainder_m']['value']
    for d in model['devices']:
        if d['ifc_class']!='IfcDuctSegment': continue
        origin=np.array(d['origin_m']); points={p['id']:origin+p['offset_m'] for p in d['ports']}
        vector=points['out']-points['in']; length=float(np.linalg.norm(vector)); unit=vector/length
        a=trims.get((d['id'],'in'),0.); b=trims.get((d['id'],'out'),0.); remaining=length-a-b
        if remaining<minimum-1e-8: raise ValueError('Authored fitting endpoints exceed inherited budget on '+d['id'])
        points['in']+=a*unit; points['out']-=b*unit
        axis=int(np.argmax(abs(unit))); origin[axis]=min(points['in'][axis],points['out'][axis])
        d['origin_m']=origin.tolist(); d['size_m'][axis]=remaining
        for p in d['ports']: p['offset_m']=(points[p['id']]-origin).tolist()
        d['properties'].update(AppliedTeeFromTrim_m=a,AppliedTeeToTrim_m=b,
            StudyStraightLength_m=remaining,AllFittingTrimsKnown=False)
        straight.specification(d)
        budgets.append(dict(section=d['id'],before_tee_length_m=length,from_tee_trim_m=a,
            to_tee_trim_m=b,remaining_m=remaining,minimum_remainder_m=minimum))
    model['name']='Partial Source Network - Verified Local Tee Integration'
    bim.validate(model)
    return model,interfaces,budgets


def snapshot(paths):
    """Use already verified sources; pin actual geometry, properties and all world frames."""
    import ifcopenshell
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    objects={}; ports={}; links=set(); libraries=[]
    for path in paths:
        file=ifcopenshell.open(str(path)); libraries.append(file)
        for obj in file.by_type('IfcDistributionElement'):
            if obj.GlobalId in objects: raise ValueError('Duplicate source body identity')
            objects[obj.GlobalId]=dict(name=obj.Name,ifc_class=obj.is_a(),shape=chain.shape_hash(obj),
                properties=chain.properties(obj),frame=placement.get_local_placement(obj.ObjectPlacement).tolist())
            for p in system.get_ports(obj):
                if p.GlobalId in ports: raise ValueError('Duplicate source port identity')
                ports[p.GlobalId]=dict(owner=obj.GlobalId,name=p.Name,direction=p.FlowDirection,
                    frame=placement.get_local_placement(p.ObjectPlacement).tolist())
        links.update((r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in file.by_type('IfcRelConnectsPorts'))
    return dict(objects=objects,ports=ports,links=sorted(links)),libraries


def external_links(expected,interfaces,rows):
    from .tee_geometry import stable_guid
    from . import rectangular_transition as transition
    result=[]
    for r in interfaces:
        row=rows[r['node']]; arm=r['arm']
        owner=stable_guid(row['children'][arm],'IfcDuctFitting',transition.KEY) if arm in row['children'] else stable_guid(row['spec'],'IfcDuctFitting','RECTANGULAR-TEE')
        name='end' if arm in row['children'] else arm
        fitting=[g for g,p in expected['ports'].items() if p['owner']==owner and p['name']==name]
        sections=[g for g,o in expected['objects'].items() if o['name']==r['section'] and o['ifc_class']=='IfcDuctSegment']
        if len(fitting)!=1 or len(sections)!=1: raise ValueError('Unique source fitting/section identity required')
        segment=[g for g,p in expected['ports'].items() if p['owner']==sections[0] and p['name']==r['port']]
        if len(segment)!=1: raise ValueError('Unique source straight endpoint required')
        a,b=(segment[0],fitting[0]) if r['port']=='out' else (fitting[0],segment[0])
        first,second=(expected['ports'][g] for g in (a,b)); x,y=(np.array(p['frame']) for p in (first,second))
        if first['direction']!='SOURCE' or second['direction']!='SINK' or not np.allclose(x[:3,3],y[:3,3],atol=1e-8,rtol=0) or not np.allclose(x[:3,2],-y[:3,2],atol=1e-8,rtol=0): raise ValueError('Native source/tee cap positions or normals differ')
        straight_frame=np.array(expected['objects'][sections[0]]['frame']); fitting_frame=np.array(expected['ports'][fitting[0]]['frame'])
        if not np.isclose(abs(np.dot(straight_frame[:3,0],fitting_frame[:3,0])),1,atol=1e-8,rtol=0) or not np.isclose(abs(np.dot(straight_frame[:3,1],fitting_frame[:3,1])),1,atol=1e-8,rtol=0): raise ValueError('Native rectangular source/tee section rolls differ')
        result.append((a,b))
    return result


def inspect(path,expected):
    import ifcopenshell
    import ifcopenshell.validate
    import ifcopenshell.util.system as system
    import ifcopenshell.util.element as element
    actual,_=snapshot([path]); file=ifcopenshell.open(str(path))
    if set(actual['objects'])!=set(expected['objects']) or set(actual['ports'])!=set(expected['ports']) or actual['links']!=expected['links'] or len(file.by_type('IfcRelConnectsPorts'))!=len(expected['links']): raise ValueError('Merged body/port/link inventory differs')
    for key in ('objects','ports'):
        for guid,record in expected[key].items():
            saved=dict(actual[key][guid]); frame=saved.pop('frame'); original=dict(record); source_frame=original.pop('frame')
            if saved!=original or not np.allclose(frame,source_frame,atol=1e-8,rtol=0): raise ValueError('Merged native geometry,properties,identity or placement differs')
    occupied=set()
    for a,b in actual['links']:
        x,y=(actual['ports'][g] for g in (a,b)); first,last=(np.array(p['frame']) for p in (x,y))
        if a in occupied or b in occupied or x['direction']!='SOURCE' or y['direction']!='SINK' or not np.allclose(first[:3,3],last[:3,3],atol=1e-8,rtol=0) or not np.allclose(first[:3,2],-last[:3,2],atol=1e-8,rtol=0): raise ValueError('Merged directed cap connection invalid')
        occupied.update((a,b))
    if file.by_type('IfcSpace') or len(file.by_type('IfcDistributionPort'))!=len(actual['ports']): raise ValueError('No temporary space or orphan port allowed')
    groups=file.by_type('IfcDistributionSystem')
    if len(groups)!=1 or groups[0].Name!='SOURCE-SUPPLY' or {o.GlobalId for rel in groups[0].IsGroupedBy for o in rel.RelatedObjects}!=set(actual['objects']): raise ValueError('Exact unified supply system required')
    for obj in file.by_type('IfcDistributionElement'):
        if len(system.get_ports(obj))!=sum(p['owner']==obj.GlobalId for p in actual['ports'].values()) or element.get_container(obj).Name!='COORDINATION-REFERENCE-PLANE': raise ValueError('Owned ports/reference containment differs')
    logger=ifcopenshell.validate.json_logger(); ifcopenshell.validate.validate(file,logger,express_rules=True)
    if logger.statements: raise ValueError('Merged IFC schema/EXPRESS validation failed: '+str(logger.statements[:2]))
    return dict(bodies=len(actual['objects']),owned_ports=len(actual['ports']),actual_links=len(actual['links']),
        boundary_ports=len(actual['ports'])-2*len(actual['links']),source_geometry_properties_frames_preserved=True,
        coincident_opposed_interfaces=True,schema_express_pass=True,complete_network=False,design_accepted=False)


def merge(paths,target,interfaces,rows):
    import ifcopenshell.api as api
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    expected,libraries=snapshot(paths); links=external_links(expected,interfaces,rows)
    expected['links']=sorted(set(map(tuple,expected['links']))|set(links))
    file=libraries[0]; storey=file.by_type('IfcBuildingStorey')[0]; distribution=file.by_type('IfcDistributionSystem')[0]
    original_links=len(file.by_type('IfcRelConnectsPorts')); original_systems=len(file.by_type('IfcDistributionSystem'))
    for library in libraries[1:]:
        reuse={}
        for obj in library.by_type('IfcDistributionElement'):
            added=api.run('project.append_asset',file,library=library,element=obj,reuse_identities=reuse,assume_asset_uniqueness_by_name=False)
            # Restore verified source world placements and object-relative owned ports.
            world=np.array(expected['objects'][obj.GlobalId]['frame']); added.ObjectPlacement=relative_placement(file,world,None)
            for port in system.get_ports(added):
                port.ObjectPlacement=relative_placement(file,np.linalg.inv(world)@np.array(expected['ports'][port.GlobalId]['frame']),added.ObjectPlacement)
            api.run('spatial.assign_container',file,products=[added],relating_structure=storey)
            api.run('system.assign_system',file,products=[added],system=distribution)
    if len(file.by_type('IfcRelConnectsPorts'))!=original_links or len(file.by_type('IfcDistributionSystem'))!=original_systems: raise ValueError('Upstream appended unexpected systems/links')
    ports={p.GlobalId:p for p in file.by_type('IfcDistributionPort')}
    present={(r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in file.by_type('IfcRelConnectsPorts')}
    for a,b in expected['links']:
        if (a,b) not in present: api.run('system.connect_port',file,port1=ports[a],port2=ports[b],direction='SOURCE')
    file.write(str(target)); return inspect(target,expected),expected


def methods():
    return [Path(__file__),Path(chain.__file__)]


def prepare(source,folder):
    result=json.loads((source/'tee-candidates.json').read_text()); selection=Path(result['source']['selection'])
    selected=json.loads((selection/'selection.json').read_text()); junction=json.loads((selection/'junction.json').read_text())
    basis=json.loads(Path(selected['source']['basis']).read_text()); policy=json.loads(Path(result['source']['policy']).read_text())
    rows=candidates.prepare(junction,basis,policy,folder/'inputs'); _,blocked=candidates.budgets(selected,rows)
    original=json.loads((selection/'native/model-input.json').read_text())
    model,interfaces,budgets=compile_model(original,junction,selected,rows,blocked)
    return result,selection,rows,blocked,model,interfaces,budgets


def run(source,out):
    source,out=[Path(p).resolve() for p in (source,out)]
    if not all(allowed(p) for p in (source,out)) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out): raise ValueError('Fresh selected workspace outside source run required')
    candidates.verify(source)
    pins={str(p):digest(p) for p in [source/'tee-candidates.json',*methods()]}
    result,selection,rows,blocked,model,interfaces,budgets=prepare(source,out)
    model_path=out/'model-input.json'; model_path.write_text(json.dumps(model,indent=2))
    bim.run(model_path,out/'bim')
    import ifcopenshell
    import ifcopenshell.api as api
    file=ifcopenshell.open(str(out/'bim/model.ifc')); storey=file.by_type('IfcBuildingStorey')[0]
    api.run('spatial.assign_container',file,products=file.by_type('IfcDuctFitting'),relating_structure=storey)
    file.write(str(out/'recontained.ifc'))
    backbone.export_storey(out/'recontained.ifc',out/'Trimmed Backbone.ifc')
    trimmed=backbone.inspect_saved(out/'Trimmed Backbone.ifc',model)
    paths=[out/'Trimmed Backbone.ifc']+[source/'models'/r['directory']/'assembly.ifc' for name,r in rows.items() if name not in blocked]
    checks,expected=merge(paths,out/'Supply Network.ifc',interfaces,rows)
    if any(digest(Path(p))!=sha for p,sha in pins.items()): raise ValueError('Source/method changed during integration')
    report=dict(source=str(source),inputs=pins,trimmed_checks=trimmed,checks=checks,interfaces=interfaces,
        budgets=budgets,blocked_nodes=blocked,other_unresolved_nodes=result['not_authored_source_nodes'],
        original_requirement_ids=result['original_requirement_ids'],original_backbone_modified=False,
        complete_network=False,design_accepted=False,
        scope='Partial source tee integration with trimmed native straights and actual IFC connections; no whole-network clash, fitting loss, products, installation or design acceptance')
    report['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'network.json').write_text(json.dumps(report,indent=2)); return report


def verify(out):
    out=Path(out).resolve()
    if not allowed(out): raise ValueError('Selected workspace required')
    report=json.loads((out/'network.json').read_text()); source=Path(report['source']); candidates.verify(source)
    if report['inputs']!={str(p):digest(p) for p in [source/'tee-candidates.json',*methods()]} or report['design_accepted'] is not False or report['complete_network'] is not False or report['original_backbone_modified'] is not False: raise ValueError('Network source/method/status differs')
    for name,sha in report['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or digest(path)!=sha: raise ValueError('Network artifact changed')
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='network-audit-') as folder:
        result,selection,rows,blocked,model,interfaces,budgets=prepare(source,Path(folder))
        if model!=json.loads((out/'model-input.json').read_text()) or interfaces!=report['interfaces'] or budgets!=report['budgets'] or blocked!=report['blocked_nodes'] or report['original_requirement_ids']!=result['original_requirement_ids'] or report['other_unresolved_nodes']!=result['not_authored_source_nodes']: raise ValueError('Network trim/source obligations differ')
        if backbone.inspect_saved(out/'Trimmed Backbone.ifc',model)!=report['trimmed_checks']: raise ValueError('Trimmed native backbone differs')
        paths=[out/'Trimmed Backbone.ifc']+[source/'models'/r['directory']/'assembly.ifc' for name,r in rows.items() if name not in blocked]
        expected,_=snapshot(paths); expected['links']=sorted(set(map(tuple,expected['links']))|set(external_links(expected,interfaces,rows)))
        check=inspect(out/'Supply Network.ifc',expected)
        if check!=report['checks']: raise ValueError('Merged saved checks differ')
    return dict(integrity_pass=True,**check)


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('source');p.add_argument('--out',required=True)
    sub.add_parser('verify').add_argument('out'); a=parser.parse_args()
    r=run(a.source,a.out)['checks'] if a.command=='run' else verify(a.out)
    print(json.dumps(r,indent=2)); return 2

if __name__=='__main__': raise SystemExit(main())
