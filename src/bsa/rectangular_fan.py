"""Bounded fixed-speed total-pressure fan intersection; one rectangular air path."""
import argparse
import copy
import json
import math
from pathlib import Path
from .engine import ProjectError
from .cli import digest
from . import pump, rectangular_network, network

MODEL='fixed-speed air fan; single fixed-total-pressure terminal; free flow'
NAMESPACE='fan/operating_point'
PENDING=['Fan curve authenticity, installation category and system effects',
         'Real fan electrical input, motor rating, efficiency and Hong Kong fan-power checks',
         'Acoustics, controls, fire/smoke and full engineering acceptance',
         'Native geometry binding and branches/loops']


def validate_curve(curve):
    if not isinstance(curve,dict) or curve.get('model')!=MODEL or curve.get('pressure_basis')!='fan total pressure rise':
        raise ProjectError('explicit fixed-speed fan TOTAL pressure curve required; no static-pressure conversion')
    c=copy.deepcopy(curve)
    c.pop('pressure_basis')
    c['model']=pump.MODEL
    if c.get('efficiency_basis')!='not supplied':raise ProjectError('fan electrical power/efficiency not supported; do not reuse water efficiency')
    pump.validate_curve(c)
    return curve


def prepare(project,curve):
    validate_curve(curve)
    converted,areas,dimensions,_=rectangular_network.prepare(project)
    _,nodes,_,outgoing,order=network.validate(converted)
    leaves=[n for n in order if not outgoing[n]]
    if len(leaves)!=1 or any(len(v)>1 for v in outgoing.values()) or any(nodes[n]['demand_m3_s']!=0 for n in order[:-1]):
        raise ProjectError('one free-flow terminal and no branches/internal withdrawals required')
    if NAMESPACE in project['sources']:raise ProjectError('reserved fan provenance namespace already present')
    for key,value in curve['fluid'].items():
        if not math.isclose(value,project['fluid'][key],rel_tol=1e-9,abs_tol=0):raise ProjectError('fan curve and network fluid mismatch; no density correction inferred')
    low=curve['flow_bracket_m3_s'][0]
    for row in project['segments']:
        reynolds=project['fluid']['density_kg_m3']*low/areas[row['id']]*dimensions[row['id']]['hydraulic_diameter_m']/project['fluid']['dynamic_viscosity_pa_s']
        if not math.isfinite(reynolds) or reynolds<4000:raise ProjectError('entire fan bracket must remain turbulent Re>=4000')
    return leaves[0]


def operating_network(project,curve,terminal,flow):
    data=copy.deepcopy(project);point=pump.interpolate(curve,flow)
    target=next(n for n in data['nodes'] if n['id']==terminal)
    data['sources'][NAMESPACE]='Free flow solved at fixed terminal total pressure; curve: '+curve['sources'][curve['source']]+'; original terminal basis: '+project['sources'][target['source']]
    target.update(demand_m3_s=flow,source=NAMESPACE)
    data['supply'].update(total_pressure_pa=curve['inlet_total_pressure_pa']+point['total_pressure_rise_pa'],source=NAMESPACE)
    return data,point


def solve(project,curve):
    result,selected=pump._solve(project,curve,prepare,rectangular_network.calculate,operating_network)
    # Shared numerical machinery uses historical pump keys; expose air-only semantics.
    for row in result['trace']:
        row['fan_total_pressure_rise_pa']=row.pop('pump_total_pressure_rise_pa')
    if result['operating_point'] is not None:
        point=result['operating_point']
        point['fan_total_pressure_rise_pa']=point.pop('pump_total_pressure_rise_pa')
        point['air_power_kw']=point.pop('hydraulic_power_kw')
        point.pop('wire_to_water_efficiency');point.pop('estimated_electrical_kw')
    result.update(model=MODEL,pending=PENDING,geometry_bound=False,regulatory_compliance='not_established',
        scope='Source-bounded fixed-speed total-pressure curve and one level constant-density rectangular path; free flow at fixed terminal total pressure; fixed route/K; not a multi-terminal flow-balancing solver',
        methods=['Reused bounded bisection/interpolation from bsa.pump; no extrapolation',
                 'Pinned fluids Colebrook through rectangular actual-area/hydraulic-diameter pressure engine',
                 'https://www.amca.org/educate/articles-and-technical-papers/amca-inmotion-articles/straightening-out-fan-curves.html'])
    return result,selected


def run(project,curve_path,out):
    import importlib.metadata
    project,curve_path,out=[Path(p).resolve() for p in (project,curve_path,out)]
    if out.exists() or any(out==p or out in p.parents for p in (project,curve_path)):raise ProjectError('new separate fan output required')
    before={str(p):digest(p) for p in (project,curve_path)}
    data=json.loads(project.read_text(encoding='utf-8-sig'));curve=json.loads(curve_path.read_text(encoding='utf-8-sig'))
    result,selected=solve(data,curve)
    out.mkdir(parents=True)
    if selected is not None:
        path=out/'operating-network.json';path.write_text(json.dumps(selected,indent=2),encoding='utf-8')
        rerun=rectangular_network.run(path,out/'analysis')
        if not math.isclose(rerun['supply_flow_m3_s'],result['operating_point']['flow_m3_s'],rel_tol=0,abs_tol=1e-15):raise ProjectError('fan operating rerun flow differs')
        result['selected_rerun_pass']=rerun['calculated_checks_pass']
        result['calculated_checks_pass'] &= result['selected_rerun_pass']
    else:result['selected_rerun_pass']=False
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('fan inputs changed')
    result.update(inputs=before,inputs_unchanged=True,curve=curve,network_sources=data['sources'],fluids_version=importlib.metadata.version('fluids'))
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'fan.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--curve',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.curve,a.out)
    print(json.dumps({k:r[k] for k in ('status','operating_point','calculated_checks_pass','design_accepted')},indent=2))
    return 0 if r['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())
