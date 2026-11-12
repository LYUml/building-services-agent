"""Explicit pump-IFC/electrical operating scenarios, retaining baseline design loads."""
import argparse
import copy
import html
import importlib.metadata
import json
import math
from pathlib import Path
from .cli import digest,run as electrical_run
from .engine import ProjectError,validate
from .cad_overlay import equivalent
from .pump import solve
from . import ifc_property_units

PSET='BSA_PumpElectrical'
LOAD_BASIS='steady operating estimate; retain baseline design load and hardware'
POSITION_BASIS='electrical XY equals pump body bounding-box centre'


def validate_link(link):
    fields={'source','electrical_device_id','pump_guid','source_port_guid','operating_power_factor','position_tolerance_m','load_basis','position_basis'}
    if not isinstance(link,dict) or set(link)!=fields or link['load_basis']!=LOAD_BASIS or link['position_basis']!=POSITION_BASIS:
        raise ProjectError('explicit pump/electrical identity, operating-load and centre-position binding required')
    for key in ('source','electrical_device_id','pump_guid','source_port_guid'):
        if not isinstance(link[key],str) or not link[key].strip():raise ProjectError('nonempty binding source and identities required')
    for key in ('operating_power_factor','position_tolerance_m'):
        if type(link[key]) not in (int,float) or not math.isfinite(link[key]) or link[key]<=0:raise ProjectError('explicit positive operating PF and position tolerance required')
    if link['operating_power_factor']>1 or link['position_tolerance_m']>.01:raise ProjectError('PF <=1 and position tolerance <=0.01 m required')
    return link


def read_pump(report_path):
    """Verify recorded bytes, then recompute the curve/network rather than trusting a scalar."""
    report_path=Path(report_path).resolve();report=json.loads(report_path.read_text(encoding='utf-8-sig'))
    if not isinstance(report,dict):raise ProjectError('pump report object required')
    roles=report.get('input_roles',{})
    if not isinstance(roles,dict) or set(roles)!={'network','curve'} or any(not isinstance(v,str) or not Path(v).is_absolute() for v in roles.values()):
        raise ProjectError('pump report requires explicit network/curve input roles; rerun older reports')
    files={key:Path(value).resolve() for key,value in roles.items()}
    hashes=report.get('inputs',{})
    if not isinstance(hashes,dict) or set(hashes)!=set(roles.values()):raise ProjectError('pump source roles/hash set mismatch')
    verified={report_path:digest(report_path)}
    for key,path in files.items():
        if not path.is_file() or digest(path)!=hashes[roles[key]]:raise ProjectError('pump source bytes changed')
        verified[path]=digest(path)
    artifacts=report.get('artifacts',{})
    if not isinstance(artifacts,dict) or not {'operating-network.json','analysis/network.json'}<=set(artifacts):raise ProjectError('complete selected pump artifacts required')
    for name,expected in artifacts.items():
        if not isinstance(name,str) or Path(name).is_absolute():raise ProjectError('invalid pump artifact path')
        path=(report_path.parent/name).resolve()
        if not path.is_relative_to(report_path.parent) or not path.is_file() or digest(path)!=expected:raise ProjectError('pump artifact changed, missing or outside report directory')
        verified[path]=expected
    if report.get('fluids_version')!=importlib.metadata.version('fluids'):raise ProjectError('pump engine version differs; rerun source analysis')
    network=json.loads(files['network'].read_text(encoding='utf-8-sig'));curve=json.loads(files['curve'].read_text(encoding='utf-8-sig'))
    if not equivalent(report.get('curve'),curve) or not equivalent(report.get('network_sources'),network.get('sources')):
        raise ProjectError('pump report source metadata differs from recorded inputs')
    replay,selected=solve(network,curve)
    if not replay['calculated_checks_pass'] or report.get('calculated_checks_pass') is not True or report.get('selected_rerun_pass') is not True:
        raise ProjectError('a passing sourced pump operating point is required')
    for key in ('status','checks','flow_bracket_m3_s','operating_point'):
        if not equivalent(report.get(key),replay.get(key)):raise ProjectError('pump report disagrees with independent replay: '+key)
    saved=json.loads((report_path.parent/'operating-network.json').read_text(encoding='utf-8-sig'))
    if not equivalent(saved,selected):raise ProjectError('saved operating input differs from pump replay')
    if replay['operating_point']['estimated_electrical_kw'] is None:raise ProjectError('combined wire-to-water efficiency required for electrical binding')
    return replay,network,files['network'],verified


def operating_project(baseline,link,point,evidence):
    """Reuse the exact steady-load projection for screening and saved IFC handoff."""
    validate(baseline);validate_link(link)
    if not isinstance(evidence,str) or not evidence.strip():raise ProjectError('Explicit operating source evidence required')
    target=next((d for d in baseline['devices'] if d['id']==link['electrical_device_id']),None)
    if target is None:raise ProjectError('unknown electrical device ID')
    operating=copy.deepcopy(baseline);operating['name']+=' / pump steady operating scenario'
    revised=next(d for d in operating['devices'] if d['id']==target['id'])
    source_key='pump-electrical/'+target['id']
    if source_key in operating['sources']:raise ProjectError('reserved operating-source namespace exists')
    operating['sources'][source_key]=link['source']+'; '+evidence+'; steady operating estimate only; baseline design load/hardware retained separately; original device basis: '+baseline['sources'][target['source']]
    revised.update(electrical_kw=point['estimated_electrical_kw'],power_factor=link['operating_power_factor'],source=source_key)
    validate(operating)
    return operating


def run(project,pump_report,ifc_path,network_binding,link_path,out):
    import numpy as np
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.system as system
    import ifcopenshell.util.element as element
    import ifcopenshell.validate
    from .network_binding import reconcile
    paths=[Path(p).resolve() for p in (project,pump_report,ifc_path,network_binding,link_path)];out=Path(out).resolve()
    project,pump_report,ifc_path,network_binding,link_path=paths
    pump,network,network_path,lineage=read_pump(pump_report)
    inputs=set(paths)|set(lineage)|{Path(__file__).resolve(),Path(ifc_property_units.__file__).resolve()}
    if any(out==p or out in p.parents for p in inputs):raise ProjectError('output must not contain source or pump evidence inputs')
    before={str(p):lineage[p] if p in lineage else digest(p) for p in inputs}
    if any(digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('pump evidence changed during binding preparation')
    baseline=validate(json.loads(project.read_text(encoding='utf-8-sig')))
    link=validate_link(json.loads(link_path.read_text(encoding='utf-8-sig')))
    binding=json.loads(network_binding.read_text(encoding='utf-8-sig'))
    model=ifcopenshell.open(str(ifc_path))
    projects=model.by_type('IfcProject')
    units=[u for p in projects if p.UnitsInContext for u in p.UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT']
    if len(projects)!=1 or len(units)!=1 or not units[0].is_a('IfcSIUnit') or units[0].Name!='METRE' or units[0].Prefix is not None:
        raise ProjectError('one project with explicit metre length units required')
    names=[d.Name for d in model.by_type('IfcDistributionElement')]
    if any(not isinstance(n,str) or not n for n in names) or len(set(names))!=len(names):raise ProjectError('unique distribution element names required for network binding')
    reconcile(ifc_path,network_path,binding)
    guids=[obj.GlobalId for obj in model.by_type('IfcRoot')]
    if len(set(guids))!=len(guids):raise ProjectError('duplicate IFC identities')
    try:obj=model.by_guid(link['pump_guid']);port=model.by_guid(link['source_port_guid'])
    except RuntimeError as exc:raise ProjectError('unknown pump or source port GUID') from exc
    if not obj.is_a('IfcPump') or not port.is_a('IfcDistributionPort') or system.get_port_element(port)!=obj or port.FlowDirection!='SOURCE':
        raise ProjectError('binding must identify an actual pump and its SOURCE port')
    if binding['nodes'][network['supply']['node']]!=obj.Name+'.'+port.Name:raise ProjectError('bound pump outlet is not the source of this network')
    first=next(s for s in network['segments'] if s['from']==network['supply']['node'])
    first_name=binding['segments'][first['id']][0]
    connected=[r.RelatedPort for r in port.ConnectedTo]+[r.RelatingPort for r in port.ConnectedFrom]
    if not any(p.FlowDirection=='SINK' and system.get_port_element(p).Name==first_name for p in connected):raise ProjectError('pump outlet lacks actual IFC connection to first network segment')
    if PSET in element.get_psets(obj):raise ProjectError('reserved pump/electrical property set already exists; preserve prior revision')
    target=next((d for d in baseline['devices'] if d['id']==link['electrical_device_id']),None)
    if target is None:raise ProjectError('unknown electrical device ID')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    shape=ifcopenshell.geom.create_shape(settings,obj);vertices=np.asarray(shape.geometry.verts).reshape(-1,3)
    if not len(vertices) or not np.all(np.isfinite(vertices)):raise ProjectError('finite pump body geometry required')
    centre=(vertices.min(axis=0)+vertices.max(axis=0))/2
    if math.dist(centre[:2],[target['x_m'],target['y_m']])>link['position_tolerance_m']:raise ProjectError('pump body centre differs from electrical XY')
    point=pump['operating_point']
    operating=operating_project(baseline,link,point,'source pump report SHA256 '+digest(pump_report))
    source_key='pump-electrical/'+target['id']
    out.mkdir(parents=True,exist_ok=False)
    baseline_result=electrical_run(project,out/'baseline-electrical')
    operating_path=out/'operating-electrical.json';operating_path.write_text(json.dumps(operating,indent=2),encoding='utf-8')
    operating_result=electrical_run(operating_path,out/'operating-electrical')
    original_entities={e.id():str(e) for e in model}
    properties=dict(ElectricalDeviceID=target['id'],CircuitID=target['circuit'],BaselineElectricalInput_kW=float(target['electrical_kw']),
        OperatingElectricalInput_kW=point['estimated_electrical_kw'],OperatingPowerFactor=link['operating_power_factor'],NominalVoltage_V=float(baseline['supply_voltage_v']),
        OperatingFlow_m3_s=point['flow_m3_s'],PumpTotalPressureRise_Pa=point['pump_total_pressure_rise_pa'],HydraulicPower_kW=point['hydraulic_power_kw'],
        WireToWaterEfficiency=point['wire_to_water_efficiency'],LoadBasis=link['load_basis'],Source=operating['sources'][source_key],PumpReportSHA256=digest(pump_report))
    properties['OperatingDeviceCurrent_A']=point['estimated_electrical_kw']*1000/link['operating_power_factor']/baseline['supply_voltage_v']
    properties['Scenario']='Calculated steady operating estimate, not measured operation, motor nameplate, starting current or full design approval'
    kinds={**{key:'power_kw' for key in ('BaselineElectricalInput_kW','OperatingElectricalInput_kW','HydraulicPower_kW')},
        **{key:'ratio' for key in ('OperatingPowerFactor','WireToWaterEfficiency')},
        **{key:'identifier' for key in ('ElectricalDeviceID','CircuitID')},
        'NominalVoltage_V':'voltage','OperatingFlow_m3_s':'flow','PumpTotalPressureRise_Pa':'pressure','OperatingDeviceCurrent_A':'current'}
    records={key:(val,kinds.get(key,'text')) for key,val in properties.items()}
    ifc_property_units.add(model,obj,PSET,records)
    selected=out/'model.ifc';model.write(str(selected));reopened=ifcopenshell.open(str(selected))
    if any(str(reopened.by_id(id))!=value for id,value in original_entities.items()):raise ProjectError('existing IFC entities changed during property-only revision')
    saved=element.get_psets(reopened.by_guid(obj.GlobalId)).get(PSET,{})
    if any(not equivalent(value,saved.get(key)) for key,value in properties.items()):raise ProjectError('saved pump electrical properties differ')
    typed_checks=ifc_property_units.inspect(reopened,reopened.by_guid(obj.GlobalId),PSET,records)
    reconcile(selected,network_path,binding)
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(reopened,logger,express_rules=True)
    (out/'schema-validation.json').write_text(json.dumps(logger.statements,default=str,indent=2),encoding='utf-8')
    if logger.statements:raise ProjectError('revised IFC schema validation failed')
    circuits={c['id']:c for c in operating_result['circuits']};circuit=circuits[target['circuit']]
    record=dict(electrical_device_id=target['id'],pump_guid=obj.GlobalId,source_port_guid=port.GlobalId,circuit_id=target['circuit'],
        baseline_electrical_kw=target['electrical_kw'],operating_electrical_kw=point['estimated_electrical_kw'],operating_power_factor=link['operating_power_factor'],
        bound_device_operating_current_a=point['estimated_electrical_kw']*1000/link['operating_power_factor']/baseline['supply_voltage_v'],
        operating_circuit_current_a=circuit['design_current_a'],pump_body_centre_m=centre.tolist())
    unchanged=all(digest(Path(p))==h for p,h in before.items())
    result=dict(inputs=before,inputs_unchanged=unchanged,record=record,pump_replayed=True,existing_ifc_entities_unchanged=True,
        saved_ifc_properties_match=True,saved_typed_properties=typed_checks,schema_valid=True,baseline_hardware_retained=baseline['circuits']==operating['circuits'],
        baseline_checks_pass=baseline_result['calculated_checks_pass'],operating_checks_pass=operating_result['calculated_checks_pass'],
        unbound_electrical_device_ids=[d['id'] for d in baseline['devices'] if d['id']!=target['id']],
        calculated_checks_pass=unchanged and baseline['circuits']==operating['circuits'] and baseline_result['calculated_checks_pass'] and operating_result['calculated_checks_pass'],design_accepted=False,
        pending=['nameplate/design rating, motor starting, fault protection and full electrical acceptance','operating PF and curve/efficiency/product evidence',
                 'other electrical devices and circuit topology in IFC','native CAD/plot and BIM-viewer review','NPSH, controls and complete engineering acceptance'])
    if not unchanged:raise ProjectError('source changed during pump/electrical binding')
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Pump electrical scenarios</title><h1>Pump electrical scenarios</h1><p>Baseline design loads and hardware retained. Operating estimate is not a nameplate rating or cable-selection basis.</p><pre>'+html.escape(json.dumps(record,indent=2))+'</pre><h2>Pending</h2><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in result['pending'])+'</ul>',encoding='utf-8')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'pump-electrical.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for key in ('pump-report','ifc','network-binding','link','out'):parser.add_argument('--'+key,required=True,type=Path)
    args=parser.parse_args();result=run(args.project,args.pump_report,args.ifc,args.network_binding,args.link,args.out)
    print(json.dumps(result['record'],indent=2));return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
