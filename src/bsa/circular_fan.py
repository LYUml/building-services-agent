"""Existing bounded fan solver applied to an exact checked circular local path."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path

from . import network,pump,rectangular_fan,route_pressure
from .cli import digest
from .engine import ProjectError
from .module_contract import read_json
from .workspace import allowed


def prepare(project,curve):
    rectangular_fan.validate_curve(curve)
    _,nodes,_,outgoing,order=network.validate(project)
    leaves=[n for n in order if not outgoing[n]]
    if len(leaves)!=1 or any(len(v)>1 for v in outgoing.values()) or any(nodes[n]['demand_m3_s']!=0 for n in order[:-1]):
        raise ProjectError('One free-flow terminal and no branches/internal withdrawals required')
    if any(nodes[n]['elevation_m']!=nodes[order[0]]['elevation_m'] for n in order):
        raise ProjectError('Fan external pressure stations must share a common elevation; no ambient/static-height conversion inferred')
    if rectangular_fan.NAMESPACE in project['sources']:raise ProjectError('Reserved fan provenance namespace already present')
    for key,value in curve['fluid'].items():
        if not math.isclose(value,project['fluid'][key],rel_tol=1e-9,abs_tol=0):raise ProjectError('Fan curve and circular path fluid mismatch; no density correction inferred')
    for segment in project['segments']:
        low=curve['flow_bracket_m3_s'][0]
        reynolds=4*project['fluid']['density_kg_m3']*low/(math.pi*project['fluid']['dynamic_viscosity_pa_s']*segment['diameter_m'])
        if not math.isfinite(reynolds) or reynolds<4000:raise ProjectError('Whole fan bracket must remain turbulent Re>=4000')
    return leaves[0]


def solve(project,curve):
    result,selected=pump._solve(project,curve,prepare,network.calculate,rectangular_fan.operating_network)
    for row in result['trace']:row['fan_total_pressure_rise_pa']=row.pop('pump_total_pressure_rise_pa')
    if result['operating_point'] is not None:
        point=result['operating_point'];point['fan_total_pressure_rise_pa']=point.pop('pump_total_pressure_rise_pa')
        point['air_power_kw']=point.pop('hydraulic_power_kw');point.pop('wire_to_water_efficiency');point.pop('estimated_electrical_kw')
    result.update(model=rectangular_fan.MODEL,geometry_bound=False,regulatory_compliance='not_established',
        pending=['Curve authenticity, stable region, installation category and system effects','Actual fan hardware/ports and updated native device flow metadata',
                 'Motor/electrical input and Hong Kong fan-power checks','Full multibranch balancing, intermediate pressure, noise and installation acceptance'],
        scope='Fixed circular local geometry/K, constant-density free flow at one fixed terminal total pressure; level external common-reference stations; no static-pressure conversion, fan electricity or branches/loops')
    return result,selected


def run(producer,curve_path,out):
    producer,curve_path,out=[Path(p).resolve() for p in (producer,curve_path,out)]
    if out.exists() or not all(allowed(p) for p in (producer,curve_path,out)) or producer==out or producer in out.parents or out in producer.parents or out==curve_path or out in curve_path.parents:
        raise ProjectError('Fresh selected-workspace fan output outside all source inputs required')
    versions={name:importlib.metadata.version(name) for name in ('fluids','ifcopenshell','numpy')}
    if versions!={'fluids':'1.3.1','ifcopenshell':'0.8.5','numpy':'2.5.4'}:raise ProjectError('Pinned pressure/native source runtimes required')
    receipt=producer/'route-pressure.json';baseline=read_json(receipt)
    if baseline.get('calculated_checks_pass') is not True or baseline.get('design_accepted') is not False:raise ProjectError('Passing source-checked local pressure producer required')
    inputs={**baseline['inputs'],**baseline['method_inputs'],str(receipt):digest(receipt),str(curve_path):digest(curve_path)}
    for name,sha in baseline['artifacts'].items():
        path=(producer/name).resolve()
        if not path.is_relative_to(producer):raise ProjectError('Pressure artifact escapes original producer')
        inputs[str(path)]=sha
    for path,sha in inputs.items():
        if not allowed(Path(path)) or digest(Path(path))!=sha:raise ProjectError('Fan upstream source, method or pressure artifact changed')
    project_path=producer/'network-input.json'
    if str(project_path) not in inputs:raise ProjectError('Exact saved derived pressure input required')
    project=read_json(project_path);curve=read_json(curve_path)
    material_paths=[Path(p) for p in baseline['inputs'] if Path(p).name=='route-material.json']
    canonical_paths=[Path(p) for p in baseline['inputs'] if Path(p).name=='model-input.json']
    joined_paths=[Path(p) for p in baseline['inputs'] if Path(p).name=='joined.ifc']
    if any(len(p)!=1 for p in (material_paths,canonical_paths,joined_paths)):
        raise ProjectError('Exact native material/canonical/joined source lineage required; a pressure flag alone is insufficient')
    material=read_json(material_paths[0]);canonical=canonical_paths[0];skeleton=canonical.parent/'network-source.json'
    if material.get('calculated_checks_pass') is not True or str(skeleton) not in baseline['inputs']:
        raise ProjectError('Passing material evidence and original network skeleton required')
    rebuilt,body_ledger=route_pressure.derive(joined_paths[0],material['local_chain_owners'],read_json(canonical),read_json(skeleton),baseline['policy'])
    if rebuilt!=project or len(body_ledger)!=len(baseline['ledger']) or any(any(row.get(k)!=v for k,v in expected.items()) for row,expected in zip(baseline['ledger'],body_ledger)):
        raise ProjectError('Native source reconstruction differs from supplied pressure input/body ledger')
    original=network.calculate(project)
    if not original['calculated_checks_pass']:raise ProjectError('Fresh original prescribed-flow check did not pass')
    if baseline['policy']['pressure_reference']!='common-elevation-datum':raise ProjectError('Explicit inherited common-reference pressure basis required')
    methods={str(Path(p).resolve()):digest(Path(p)) for p in (__file__,network.__file__,pump.__file__,rectangular_fan.__file__,route_pressure.__file__)}
    result,selected=solve(project,curve)
    out.mkdir(parents=True)
    if selected is not None:
        path=out/'operating-network.json';path.write_text(json.dumps(selected,indent=2),encoding='utf-8')
        rerun=network.run(path,out/'analysis')
        if not math.isclose(rerun['supply_flow_m3_s'],result['operating_point']['flow_m3_s'],rel_tol=0,abs_tol=1e-15) or rerun['segments']!=result['network_analysis']['segments']:
            raise ProjectError('Fresh fan operating-network rerun differs')
        result['selected_rerun_pass']=rerun['calculated_checks_pass'];result['calculated_checks_pass'] &= rerun['calculated_checks_pass']
    else:result['selected_rerun_pass']=False
    if any(digest(Path(p))!=sha for p,sha in {**inputs,**methods}.items()):raise ProjectError('Fan source or method changed during execution')
    result.update(inputs=inputs,method_inputs=methods,runtime_versions=versions,curve=curve,geometry_bound=True,
                  native_binding_scope='Exact material-checked local chain geometry/bore/K and extended open pressure stations; no native fan equipment or installed product selection',
                  boundary_ports=baseline['boundary_ports'],source_body_guids=[r['owner_guid'] for r in baseline['ledger']],
                  original_prescribed_flow_m3_s=original['supply_flow_m3_s'],original_pressure_source_report_sha256=digest(receipt))
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'fan.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer',type=Path);parser.add_argument('--curve',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=run(args.producer,args.curve,args.out);print(json.dumps({k:result[k] for k in ('status','operating_point','calculated_checks_pass','design_accepted')},indent=2));raise SystemExit(0 if result['calculated_checks_pass'] else 2)
