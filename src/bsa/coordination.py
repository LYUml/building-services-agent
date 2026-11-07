"""Generate and reconcile electrical calculations, CAD and IFC from shared data."""
import argparse
import csv
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError


def compile_model(electrical,geometry):
    from .engine import validate as validate_electrical
    from .bim import validate as validate_bim
    validate_electrical(electrical)
    if not isinstance(geometry,dict) or geometry.get('xy_reference')!='electrical device centre':
        raise ProjectError('geometry must declare electrical device centre XY reference')
    sources=geometry.get('sources');rows=geometry.get('devices');spaces=geometry.get('spaces')
    if not isinstance(sources,dict) or not isinstance(rows,list) or not isinstance(spaces,list):
        raise ProjectError('geometry sources, spaces and device envelopes required')
    mapped={}
    allowed={'id','space','z_m','size_m','ifc_class','source'}
    for row in rows:
        if not isinstance(row,dict) or set(row)!=allowed:
            raise ProjectError('geometry device fields must be id/space/z_m/size_m/ifc_class/source; do not duplicate XY, power or circuit')
        if not isinstance(row['id'],str) or row['id'] in mapped:raise ProjectError('unique envelope IDs required')
        if not isinstance(row['source'],str) or row['source'] not in sources:raise ProjectError('unknown envelope source')
        if type(row['z_m']) not in (int,float) or not math.isfinite(row['z_m']):raise ProjectError('finite envelope z_m required')
        size=row['size_m']
        if not isinstance(size,list) or len(size)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in size):
            raise ProjectError('positive envelope dimensions required')
        mapped[row['id']]=row
    if set(mapped)!={d['id'] for d in electrical['devices']}:
        raise ProjectError('envelope IDs must exactly match electrical device IDs')
    merged={f'electrical/{key}':value for key,value in electrical['sources'].items()}
    merged.update({f'geometry/{key}':value for key,value in sources.items()})
    model=dict(name=electrical['name'],geometry_scope='axis-aligned bounding envelopes',sources=merged,
               spaces=[],systems=[],devices=[],connections=[])
    for space in spaces:
        if not isinstance(space,dict) or space.get('source') not in sources:raise ProjectError('unknown space source')
        model['spaces'].append(dict(space,source='geometry/'+space['source']))
    for circuit in electrical['circuits']:
        model['systems'].append(dict(id=circuit['id'],predefined_type='ELECTRICAL',source='electrical/'+circuit['source'],
            properties=dict(CircuitID=circuit['id'],Phase=circuit['phase'],BreakerRating_A=float(circuit['breaker_a']),
                            DemandFactor=float(circuit['demand_factor']),NominalVoltage_V=float(electrical['supply_voltage_v']))))
    for device in electrical['devices']:
        row=mapped[device['id']];w,d,h=row['size_m']
        model['devices'].append(dict(id=device['id'],ifc_class=row['ifc_class'],space=row['space'],system=device['circuit'],
            origin_m=[device['x_m']-w/2,device['y_m']-d/2,row['z_m']],size_m=row['size_m'],
            electrical_kw=device['electrical_kw'],source='electrical/'+device['source'],
            properties=dict(CircuitID=device['circuit'],PowerFactor=float(device['power_factor']),
                EnvelopeSource=sources[row['source']],XYReference='electrical device centre')))
    validate_bim(model)
    return model


def reconcile(electrical,ifc_path,dxf_path,calculations_path):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as util
    import numpy as np
    import ezdxf
    from .engine import calculate
    expected=calculate(electrical)
    saved=json.loads(Path(calculations_path).read_text(encoding='utf-8'))
    if saved.get('device_count')!=len(electrical['devices']):raise ProjectError('calculation device count mismatch')
    if saved.get('calculated_checks_pass')!=expected['calculated_checks_pass'] or saved.get('design_accepted') is not False:
        raise ProjectError('saved calculation check/acceptance status mismatch')
    saved_circuits=saved.get('circuits',[])
    if len(saved_circuits)!=len(expected['circuits']) or {c.get('id') for c in saved_circuits}!={c['id'] for c in expected['circuits']}:
        raise ProjectError('saved calculation circuit set mismatch')
    model=ifcopenshell.open(ifc_path)
    devices=model.by_type('IfcDistributionElement')
    if len(devices)!=len(electrical['devices']) or {x.Name for x in devices}!={d['id'] for d in electrical['devices']}:
        raise ProjectError('coordinated IFC device set differs from electrical data')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    records=[]
    for d in electrical['devices']:
        matches=[x for x in devices if x.Name==d['id']]
        if len(matches)!=1:raise ProjectError('IFC device identity is ambiguous')
        obj=matches[0];properties=util.get_psets(obj).get('BSA_DesignInputs',{})
        groups={r.RelatingGroup.Name for r in obj.HasAssignments if r.is_a('IfcRelAssignsToGroup')}
        shape=ifcopenshell.geom.create_shape(settings,obj)
        verts=np.array(shape.geometry.verts).reshape(-1,3)
        centre=(verts.min(axis=0)+verts.max(axis=0))/2
        if groups!={d['circuit']} or properties.get('CircuitID')!=d['circuit']:
            raise ProjectError('IFC circuit differs from electrical assignment')
        if properties.get('Source')!=electrical['sources'][d['source']]:raise ProjectError('IFC source description differs from common input')
        for key,value in (('ElectricalInput_kW',d['electrical_kw']),('PowerFactor',d['power_factor'])):
            if type(properties.get(key)) not in (int,float) or not math.isclose(properties[key],value,rel_tol=0,abs_tol=1e-10):
                raise ProjectError(f'IFC {key} differs from electrical input')
        if not np.allclose(centre[:2],[d['x_m'],d['y_m']],atol=1e-7,rtol=0):
            raise ProjectError('IFC device XY centre differs from CAD/electrical input')
        records.append(dict(id=d['id'],global_id=obj.GlobalId,circuit=d['circuit'],x_m=float(centre[0]),y_m=float(centre[1]),
                            electrical_kw=properties['ElectricalInput_kW'],power_factor=properties['PowerFactor']))
    systems=model.by_type('IfcDistributionSystem')
    if len(systems)!=len(electrical['circuits']):raise ProjectError('IFC circuit count mismatch')
    actual_systems={s.Name:s for s in systems}
    if set(actual_systems)!={c['id'] for c in electrical['circuits']}:raise ProjectError('IFC circuit set mismatch')
    for c in electrical['circuits']:
        props=util.get_psets(actual_systems[c['id']]).get('BSA_DesignInputs',{})
        if props.get('Source')!=electrical['sources'][c['source']]:raise ProjectError('IFC circuit source mismatch')
        for key,value in (('CircuitID',c['id']),('Phase',c['phase']),('BreakerRating_A',float(c['breaker_a'])),('DemandFactor',float(c['demand_factor'])),('NominalVoltage_V',float(electrical['supply_voltage_v']))):
            if props.get(key)!=value:raise ProjectError('IFC circuit properties differ from electrical input')
    cad=ezdxf.readfile(dxf_path).modelspace()
    circles=sorted((round(e.dxf.center.x,8),round(e.dxf.center.y,8)) for e in cad.query('CIRCLE'))
    expected_circles=sorted((round(d['x_m'],8),round(d['y_m'],8)) for d in electrical['devices'])
    labels=sorted((e.dxf.text,round(e.dxf.insert.x,8),round(e.dxf.insert.y,8)) for e in cad.query('TEXT'))
    expected_labels=sorted((d['id']+' / '+d['circuit'],round(d['x_m']+0.2,8),round(d['y_m'],8)) for d in electrical['devices'])
    if circles!=expected_circles or labels!=expected_labels:raise ProjectError('CAD geometry or labels differ from electrical input')
    for c in expected['circuits']:
        ds=[d for d in records if d['circuit']==c['id']]
        stored=next(x for x in saved_circuits if x['id']==c['id'])
        if stored.get('phase')!=c['phase'] or stored.get('source')!=c['source']:raise ProjectError('saved circuit phase/source mismatch')
        if sorted(stored.get('device_ids',[]))!=sorted(d['id'] for d in ds):raise ProjectError('saved calculation circuit membership mismatch')
        if stored.get('checks')!=c['checks']:raise ProjectError('saved circuit check results mismatch')
        for key in ('connected_electrical_kw','connected_va','demand_va','design_current_a','effective_ampacity_a','voltage_drop_v','voltage_drop_percent'):
            if type(stored.get(key)) not in (int,float) or not math.isclose(stored[key],c[key],rel_tol=0,abs_tol=1e-8):
                raise ProjectError('saved calculation values differ from common electrical inputs')
        if not math.isclose(sum(d['electrical_kw'] for d in ds),c['connected_electrical_kw'],abs_tol=1e-10):
            raise ProjectError('IFC/calculation circuit kW mismatch')
        if not math.isclose(sum(d['electrical_kw']*1000/d['power_factor'] for d in ds),c['connected_va'],abs_tol=1e-8):
            raise ProjectError('IFC/calculation circuit VA mismatch')
    return records


def run(project,geometry_path,out):
    from .cli import run as electrical_run
    from .bim import run as bim_run
    project,geometry_path,out=project.resolve(),geometry_path.resolve(),out.resolve()
    if any(out==p or out in p.parents for p in (project,geometry_path)):raise ProjectError('output must not contain inputs')
    before={str(p):digest(p) for p in (project,geometry_path)}
    electrical=json.loads(project.read_text(encoding='utf-8-sig'))
    model=compile_model(electrical,json.loads(geometry_path.read_text(encoding='utf-8-sig')))
    out.mkdir(parents=True,exist_ok=False)
    model_path=out/'ifc-input.json';model_path.write_text(json.dumps(model,indent=2),encoding='utf-8')
    calc=electrical_run(project,out/'electrical');bim=bim_run(model_path,out/'bim')
    records=reconcile(electrical,out/'bim/model.ifc',out/'electrical/devices.dxf',out/'electrical/calculations.json')
    with (out/'coordinated-devices.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    unchanged=all(digest(Path(p))==sha for p,sha in before.items())
    result=dict(inputs=before,inputs_unchanged=unchanged,coordination_checks_pass=True,
        electrical_checks_pass=calc['calculated_checks_pass'],bim_checks_pass=bim['model_checks_pass'],
        calculated_checks_pass=unchanged and calc['calculated_checks_pass'] and bim['model_checks_pass'],
        devices=records,design_accepted=False,
        scope='Same electrical IDs/XY/power/PF/circuits feed calculations, DXF and IFC envelopes. DWG uses the existing native adapter separately.',
        pending=['full electrical protection and photometry','physical geometry and routing','native DWG/plot and visual acceptance'])
    result['artifacts']={f.relative_to(out).as_posix():digest(f) for f in out.rglob('*') if f.is_file()}
    (out/'coordination.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not unchanged:raise ProjectError('input changed during coordinated generation')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    p.add_argument('--geometry',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.geometry,a.out)
    print(json.dumps({k:r[k] for k in ('coordination_checks_pass','calculated_checks_pass','design_accepted')}))
    return 0 if r['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())
