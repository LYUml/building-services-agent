"""Write a source-replayed operating airflow scenario without changing native geometry."""
import argparse
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.element as element
import ifcopenshell.validate
import numpy as np

from . import circular_fan,circular_fan_selection,route_join
from .cli import digest
from .duct_fitting_chain import properties,value
from .engine import ProjectError
from .module_contract import read_json
from .network import GRAVITY
from .workspace import allowed

BODY='BSA_CalculatedAirflowScenario'
PORT='BSA_CalculatedPortAirflowScenario'
TYPES={'flow':'IfcVolumetricFlowRateMeasure','pressure':'IfcPressureMeasure','text':'IfcText'}
SCOPE='Computed single-path curve scenario, not measured operation or installed fan/product approval; common-reference total pressures, original geometry/K assumptions retained'


def unit_signature(unit):
    if unit is None:return None
    if unit.is_a('IfcSIUnit'):return ('SI',unit.UnitType,unit.Name,unit.Prefix)
    if unit.is_a('IfcDerivedUnit'):return ('DERIVED',unit.UnitType,tuple(sorted((unit_signature(e.Unit),e.Exponent) for e in unit.Elements)))
    raise ProjectError('Explicit supported SI property unit required')


UNITS={'flow':('DERIVED','VOLUMETRICFLOWRATEUNIT',((('SI','LENGTHUNIT','METRE',None),3),(('SI','TIMEUNIT','SECOND',None),-1))),
       'pressure':('SI','PRESSUREUNIT','PASCAL',None),'text':None}


def native_value(item):
    return json.loads(json.dumps(value(item),ensure_ascii=False))


def measured_properties(model):
    objects=[p for p in model.by_type('IfcSimpleProperty') if not p.is_a('IfcPropertyReferenceValue')]+model.by_type('IfcPhysicalSimpleQuantity')
    return {str(p.id()):native_value(p) for p in objects}


def read_operation(producer):
    producer=Path(producer).resolve()
    if not allowed(producer):raise ProjectError('Selected operating-source workspace required')
    path=producer/'fan.json';report=read_json(path);roles=report.get('input_roles')
    if not isinstance(roles,dict) or set(roles)!={'pressure_producer','curve'} or any(not isinstance(p,str) or not Path(p).is_absolute() or not allowed(Path(p)) for p in roles.values()):
        raise ProjectError('Explicit pressure/curve source roles required; regenerate older fan reports')
    if report.get('calculated_checks_pass') is not True or report.get('selected_rerun_pass') is not True or report.get('design_accepted') is not False:raise ProjectError('Passing unaccepted native operating scenario required')
    pins={**report['inputs'],**report['method_inputs'],str(path):digest(path)}
    for name,sha in report['artifacts'].items():
        artifact=(producer/name).resolve()
        if not artifact.is_relative_to(producer):raise ProjectError('Operating artifact escapes producer')
        pins[str(artifact)]=sha
    for p,sha in pins.items():
        if not allowed(Path(p)) or digest(Path(p))!=sha:raise ProjectError('Operating source, method or artifact changed')
    pressure=Path(roles['pressure_producer']);curve_path=Path(roles['curve'])
    project,baseline,inputs,versions=circular_fan.source_project(pressure)
    if report.get('runtime_versions')!=versions or any(report['inputs'].get(p)!=sha for p,sha in inputs.items()) or report['inputs'].get(str(curve_path))!=digest(curve_path):raise ProjectError('Operating role/source identity differs')
    curve=read_json(curve_path)
    if report.get('curve')!=curve:raise ProjectError('Operating curve differs from pinned source')
    fresh,selected=circular_fan.solve(project,curve)
    if not fresh['calculated_checks_pass'] or any(report.get(k)!=fresh.get(k) for k in ('status','checks','operating_point','flow_bracket_m3_s')):raise ProjectError('Operating result differs from fresh curve/network solve')
    if read_json(producer/'operating-network.json')!=selected:raise ProjectError('Saved operating input differs from replay')
    analysis=read_json(producer/'analysis/network.json')
    if any(analysis.get(k)!=fresh['network_analysis'].get(k) for k in ('segments','nodes','supply_flow_m3_s','calculated_checks_pass')):raise ProjectError('Saved operating analysis differs from replay')
    if 'selection' in report:
        selection=report['selection'];folder=Path(selection['producer']);catalogue=Path(selection['catalogue'])
        if not all(allowed(p) for p in (folder,catalogue)) or report['inputs'].get(str(folder/'fan-selection.json'))!=digest(folder/'fan-selection.json') or report['inputs'].get(str(catalogue))!=digest(catalogue):raise ProjectError('Selection source identity differs')
        if circular_fan_selection.selected_input(folder,pressure,catalogue)!=curve_path:raise ProjectError('Selected curve handoff differs')
        chosen=read_json(folder/'fan-selection.json')['selected']
        if any(selection.get(k)!=chosen[k] for k in ('id','preference')):raise ProjectError('Selected candidate identity differs')
    if report.get('source_body_guids')!=[r['owner_guid'] for r in baseline['ledger']] or report.get('boundary_ports')!=baseline['boundary_ports']:raise ProjectError('Native operating body/port binding differs')
    joined=[Path(p) for p in inputs if Path(p).name=='joined.ifc']
    if len(joined)!=1:raise ProjectError('One exact source joined IFC required')
    return joined[0],report,fresh,baseline,selected,pins


def scenario_records(report,fresh,baseline,project,source_sha,fan_sha,curve_sha):
    point=fresh['operating_point'];segment=fresh['network_analysis']['segments'][0]
    gradient=segment['friction_pa']/baseline['length_m'];dynamic=project['fluid']['density_kg_m3']*segment['velocity_m_s']**2/2
    pressure=point['supply_total_pressure_pa'];bodies={};ports={}
    common={'Scenario':(SCOPE,'text'),'SourceIFCSHA256':(source_sha,'text'),'SourceFanResultSHA256':(fan_sha,'text'),'SourceCurveSHA256':(curve_sha,'text'),
            'CurveCandidate':(report.get('selection',{}).get('id','Supplied curve; no catalogue identity asserted'),'text')}
    for row in baseline['ledger']:
        friction=gradient*row['length_m'];body=dynamic*row['body_excess_k'];interface=dynamic*row['downstream_interface_excess_k'];elevation=project['fluid']['density_kg_m3']*GRAVITY*(row['to_point_m'][2]-row['from_point_m'][2])
        outlet=pressure-friction-body-elevation;following=outlet-interface
        values=dict(common);values.update(OperatingFlowRate=(point['flow_m3_s'],'flow'),MinimumDesignFlowRate=(fresh['design_flow_m3_s'],'flow'),InletTotalPressure=(pressure,'pressure'),OutletTotalPressure=(outlet,'pressure'),FollowingInletTotalPressure=(following,'pressure'),StraightFrictionPressureDrop=(friction,'pressure'),BodyExcessPressureDrop=(body,'pressure'),FollowingInterfacePressureDrop=(interface,'pressure'),ElevationPressureTerm=(elevation,'pressure'))
        bodies[row['owner_guid']]=values
        for port,p in [(row['inlet_port_guid'],pressure),(row['outlet_port_guid'],outlet)]:
            if port in ports:raise ProjectError('Each operating port must be owned once')
            ports[port]=dict(common,OperatingFlowRate=(point['flow_m3_s'],'flow'),TotalPressure=(p,'pressure'))
        pressure=following
    end=next(n['total_pressure_pa'] for n in fresh['network_analysis']['nodes'] if n['id']==fresh['terminal_node'])
    if not math.isclose(pressure,end,rel_tol=0,abs_tol=1e-8):raise ProjectError('Per-body operating pressures do not reconcile to terminal result')
    return dict(bodies=bodies,ports=ports)


def inspect(target,expected):
    model=ifcopenshell.open(str(target));actual=route_join.snapshot(model);before=expected['before']
    for section in ('objects','ports'):
        if set(actual[section])!=set(before[section]):raise ProjectError('Original native element/port inventory changed')
        for guid,row in before[section].items():
            saved=actual[section][guid]
            if section=='objects' and guid in expected['records']['bodies']:saved['properties'].pop(BODY,None)
            if any(saved[k]!=v for k,v in row.items() if k!='frame') or not np.allclose(saved['frame'],row['frame'],atol=1e-9,rtol=0):raise ProjectError('Original geometry/property/placement/port state changed')
    if actual['systems']!=before['systems'] or actual['links']!=before['links'] or not set(before['roots'])<=set(actual['roots']):raise ProjectError('Original system, directed connections or roots changed')
    if native_value(model.by_type('IfcProject')[0].UnitsInContext)!=expected['project_units']:raise ProjectError('Original project unit assignment changed')
    current_properties=measured_properties(model)
    if any(current_properties.get(key)!=row for key,row in expected['measured_properties'].items()):raise ProjectError('Original value datatype, explicit unit or measured quantity changed')
    for guid,old in expected['port_properties'].items():
        current=properties(model.by_guid(guid))
        if guid in expected['records']['ports']:current.pop(PORT,None)
        if current!=old:raise ProjectError('Original port properties changed')
    for guid,kind in expected['element_types'].items():
        if getattr(model.by_guid(guid),'PredefinedType',None)!=kind:raise ProjectError('Original native predefined type changed')
    count=0
    for section,name in [('bodies',BODY),('ports',PORT)]:
        for guid,values in expected['records'][section].items():
            obj=model.by_guid(guid);sets=[r.RelatingPropertyDefinition for r in obj.IsDefinedBy if r.is_a('IfcRelDefinesByProperties') and r.RelatingPropertyDefinition.is_a('IfcPropertySet') and r.RelatingPropertyDefinition.Name==name]
            if len(sets)!=1:raise ProjectError('Exactly one calculated scenario set per target required')
            props={p.Name:p for p in sets[0].HasProperties}
            if len(props)!=len(sets[0].HasProperties) or set(props)!=set(values):raise ProjectError('Exact calculated scenario property coverage required')
            for key,(wanted,kind) in values.items():
                prop=props[key]
                if not prop.is_a('IfcPropertySingleValue') or prop.NominalValue is None or prop.NominalValue.is_a()!=TYPES[kind] or unit_signature(prop.Unit)!=UNITS[kind]:raise ProjectError('Calculated value type or explicit unit differs')
                observed=prop.NominalValue.wrappedValue
                matches=observed==wanted if kind=='text' else math.isclose(observed,wanted,rel_tol=0,abs_tol=1e-10)
                if not matches:raise ProjectError('Saved calculated scenario value differs')
                count+=1
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(model,logger,express_rules=True)
    if logger.statements:raise ProjectError('Saved operating scenario IFC schema/EXPRESS check failed')
    return dict(original_geometry_and_properties_preserved=True,original_ports_systems_links_preserved=True,original_project_units_preserved=True,typed_explicit_units_pass=True,schema_valid=True,body_count=len(expected['records']['bodies']),port_count=len(expected['records']['ports']),property_count=count)


def annotate(source,target,records):
    model=ifcopenshell.open(str(source));before=route_join.snapshot(model)
    if len(model.by_type('IfcProject'))!=1:raise ProjectError('One source project required')
    for section,name in [('bodies',BODY),('ports',PORT)]:
        for guid in records[section]:
            if guid not in (before['objects'] if section=='bodies' else before['ports']):raise ProjectError('Scenario target is not an original owned native object')
            if BODY in properties(model.by_guid(guid)) or PORT in properties(model.by_guid(guid)):raise ProjectError('Calculated scenario namespace already exists; original values are not overwritten')
    expected=dict(before=before,records=records,project_units=native_value(model.by_type('IfcProject')[0].UnitsInContext),measured_properties=measured_properties(model),port_properties={p.GlobalId:properties(p) for p in model.by_type('IfcDistributionPort')},element_types={o.GlobalId:getattr(o,'PredefinedType',None) for o in model.by_type('IfcElement')})
    metre=model.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Name='METRE');second=model.create_entity('IfcSIUnit',UnitType='TIMEUNIT',Name='SECOND')
    flow=model.create_entity('IfcDerivedUnit',Elements=[model.create_entity('IfcDerivedUnitElement',Unit=metre,Exponent=3),model.create_entity('IfcDerivedUnitElement',Unit=second,Exponent=-1)],UnitType='VOLUMETRICFLOWRATEUNIT')
    units={'flow':flow,'pressure':model.create_entity('IfcSIUnit',UnitType='PRESSUREUNIT',Name='PASCAL'),'text':None}
    for section,name in [('bodies',BODY),('ports',PORT)]:
        for guid,values in records[section].items():
            pset=api.run('pset.add_pset',model,product=model.by_guid(guid),name=name)
            api.run('pset.edit_pset',model,pset=pset,properties={k:model.create_entity(TYPES[kind],v) for k,(v,kind) in values.items()})
            for prop in pset.HasProperties:prop.Unit=units[values[prop.Name][1]]
    model.write(str(target));return inspect(target,expected),expected


def run(producer,out):
    producer,out=[Path(p).resolve() for p in (producer,out)]
    if out.exists() or not allowed(out) or out==producer or out in producer.parents or producer in out.parents:raise ProjectError('Fresh metadata output outside original operating source required')
    source,report,fresh,baseline,project,pins=read_operation(producer)
    protected=[source.parent]
    if 'selection' in report:protected.append(Path(report['selection']['producer']).resolve())
    if any(out==p or p in out.parents or out in p.parents for p in protected):raise ProjectError('Metadata output must remain outside immutable native/selection source folders')
    methods={str(Path(p).resolve()):digest(Path(p)) for p in (__file__,route_join.__file__,circular_fan.__file__,circular_fan_selection.__file__,properties.__code__.co_filename)}
    records=scenario_records(report,fresh,baseline,project,digest(source),digest(producer/'fan.json'),digest(Path(report['input_roles']['curve'])))
    out.mkdir(parents=True);target=out/'Operating Airflow Study.ifc';checks,expected=annotate(source,target,records)
    if any(digest(Path(p))!=sha for p,sha in {**pins,**methods}.items()):raise ProjectError('Operating scenario source or method changed during metadata writing')
    (out/'scenario-snapshot.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
    result=dict(inputs=pins,method_inputs=methods,checks=checks,ifc_sha256=digest(target),snapshot_sha256=digest(out/'scenario-snapshot.json'),operating_point=fresh['operating_point'],minimum_design_flow_m3_s=fresh['design_flow_m3_s'],calculated_checks_pass=True,design_accepted=False,
        scope='Typed explicitly unit-bound calculated local airflow/total-pressure properties on original bodies and ports; original design properties/geometry preserved. No fan equipment, measured operation, whole-system or regulatory acceptance')
    (out/'fan-metadata.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=run(args.producer,args.out);print(json.dumps(result['checks'],indent=2))
