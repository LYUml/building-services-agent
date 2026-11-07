"""Source-bounded fixed-speed liquid pump/system intersection for a single line."""
import argparse
import copy
import csv
import html
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network import validate, calculate, run as analyse

MODEL='fixed-speed liquid pump; single fixed-total-pressure terminal; free flow'


def validate_curve(curve):
    fields={'model','sources','source','speed_rpm','fluid','inlet_total_pressure_pa','efficiency_basis','points','flow_bracket_m3_s','flow_tolerance_m3_s','pressure_tolerance_pa','max_iterations'}
    if not isinstance(curve,dict) or set(curve)!=fields or curve['model']!=MODEL:
        raise ProjectError('explicit single-line fixed-speed pump curve contract required')
    sources=curve['sources']
    if not isinstance(sources,dict) or not sources or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip() for k,v in sources.items()):
        raise ProjectError('pump curve sources required')
    if not isinstance(curve['source'],str) or curve['source'] not in sources:raise ProjectError('known pump curve source required')
    def number(value,positive=False):
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or positive and value==0:
            raise ProjectError('finite nonnegative pump data and positive solver/flow values required')
    for key in ('speed_rpm','flow_tolerance_m3_s','pressure_tolerance_pa'):number(curve[key],True)
    number(curve['inlet_total_pressure_pa'])
    if type(curve['max_iterations']) is not int or not 1<=curve['max_iterations']<=200:raise ProjectError('explicit 1..200 iteration budget required')
    fluid=curve['fluid']
    if not isinstance(fluid,dict) or set(fluid)!={'density_kg_m3','dynamic_viscosity_pa_s'}:raise ProjectError('curve fluid density and viscosity required')
    for value in fluid.values():number(value,True)
    points=curve['points'];efficiency=curve['efficiency_basis']=='wire to water'
    if curve['efficiency_basis'] not in ('wire to water','not supplied'):raise ProjectError('explicit wire-to-water or absent efficiency basis required')
    if not isinstance(points,list) or not 2<=len(points)<=1000:raise ProjectError('2..1000 sourced curve points required')
    expected={'flow_m3_s','total_pressure_rise_pa'}|({'wire_to_water_efficiency'} if efficiency else set())
    for point in points:
        if not isinstance(point,dict) or set(point)!=expected:raise ProjectError('uniform flow/total-pressure points and declared efficiency basis required')
        number(point['flow_m3_s']);number(point['total_pressure_rise_pa'])
        if efficiency:
            number(point['wire_to_water_efficiency'],point['flow_m3_s']>0)
            if point['wire_to_water_efficiency']>1:raise ProjectError('efficiency must be <=1')
    if any(a['flow_m3_s']>=b['flow_m3_s'] or a['total_pressure_rise_pa']<=b['total_pressure_rise_pa'] for a,b in zip(points,points[1:])):
        raise ProjectError('strictly increasing flow and decreasing pump pressure required; no reordering or extrapolation')
    bracket=curve['flow_bracket_m3_s']
    if not isinstance(bracket,list) or len(bracket)!=2:raise ProjectError('explicit positive operating-flow bracket required')
    for value in bracket:number(value,True)
    if not points[0]['flow_m3_s']<=bracket[0]<bracket[1]<=points[-1]['flow_m3_s']:
        raise ProjectError('operating bracket must lie within supplied curve points')
    return curve


def prepare(network,curve):
    validate_curve(curve);_,nodes,_,outgoing,order=validate(network)
    leaves=[n for n in order if not outgoing[n]]
    if len(leaves)!=1 or any(len(v)>1 for v in outgoing.values()) or any(nodes[n]['demand_m3_s']!=0 for n in order[:-1]):
        raise ProjectError('one terminal with zero internal withdrawals required; branches/loops are not solved')
    for key,value in curve['fluid'].items():
        if not math.isclose(value,network['fluid'][key],rel_tol=1e-9,abs_tol=0):raise ProjectError('pump curve and network fluid mismatch')
    low,high=curve['flow_bracket_m3_s']
    rho=network['fluid']['density_kg_m3'];mu=network['fluid']['dynamic_viscosity_pa_s']
    for segment in network['segments']:
        rlow=4*rho*low/(math.pi*mu*segment['diameter_m']);rhigh=4*rho*high/(math.pi*mu*segment['diameter_m'])
        if not (rhigh<2000 or rlow>=4000):raise ProjectError('curve domain crosses unsupported transitional Reynolds range; provide a justified model/domain')
    if 'pump/operating_point' in network['sources']:raise ProjectError('reserved pump provenance namespace already present')
    return leaves[0]


def interpolate(curve,flow):
    points=curve['points']
    if not points[0]['flow_m3_s']<=flow<=points[-1]['flow_m3_s']:raise ProjectError('pump curve extrapolation is forbidden')
    for a,b in zip(points,points[1:]):
        if a['flow_m3_s']<=flow<=b['flow_m3_s']:
            fraction=(flow-a['flow_m3_s'])/(b['flow_m3_s']-a['flow_m3_s'])
            result={key:a[key]+fraction*(b[key]-a[key]) for key in a if key!='flow_m3_s'}
            return result
    raise ProjectError('flow is not covered by pump curve')


def operating_network(network,curve,terminal,flow):
    data=copy.deepcopy(network);point=interpolate(curve,flow)
    terminal_row=next(n for n in data['nodes'] if n['id']==terminal)
    data['sources']['pump/operating_point']='Solved free flow at fixed terminal total-pressure boundary; curve: '+curve['sources'][curve['source']]+'; original terminal basis: '+network['sources'][terminal_row['source']]
    terminal_row.update(demand_m3_s=flow,source='pump/operating_point')
    data['supply'].update(total_pressure_pa=curve['inlet_total_pressure_pa']+point['total_pressure_rise_pa'],source='pump/operating_point')
    return data,point


def solve(network,curve):
    terminal=prepare(network,curve);trace=[]
    target=next(n for n in network['nodes'] if n['id']==terminal)
    def evaluate(flow):
        data,point=operating_network(network,curve,terminal,flow);analysis=calculate(data)
        system=target['required_total_pressure_pa']+math.fsum(s['dissipative_loss_pa']+s['elevation_pressure_pa'] for s in analysis['segments'])-curve['inlet_total_pressure_pa']
        row=dict(flow_m3_s=flow,pump_total_pressure_rise_pa=point['total_pressure_rise_pa'],system_required_rise_pa=system,
                 residual_pa=point['total_pressure_rise_pa']-system)
        if not all(math.isfinite(v) for v in row.values()):raise ProjectError('derived pump/system values overflowed')
        trace.append(row);return row
    lo,hi=curve['flow_bracket_m3_s']
    left,right=evaluate(lo),evaluate(hi)
    result=dict(status='not_bracketed',operating_point=None,calculated_checks_pass=False,design_accepted=False,
                design_flow_m3_s=target['demand_m3_s'],terminal_node=terminal,trace=trace,
                pending=['curve and wire-to-water efficiency/product applicability','NPSH, suction absolute pressure, cavitation and operating-region limits',
                         'motor rating/starting and electrical circuit reconciliation','controls, branches/loops and full engineering acceptance'])
    if left['residual_pa']<0 or right['residual_pa']>0:
        result['reason']='No sign bracket in the declared operating-flow interval; no flow extrapolated'
        return result,None
    if left['residual_pa']==0:hi=lo;right=left
    elif right['residual_pa']==0:lo=hi;left=right
    for iteration in range(curve['max_iterations']+1):
        if hi-lo<=curve['flow_tolerance_m3_s'] and abs(left['residual_pa'])<=curve['pressure_tolerance_pa']:break
        if iteration==curve['max_iterations']:
            result.update(status='not_converged',reason='Explicit solver iteration budget exhausted',flow_bracket_m3_s=[lo,hi]);return result,None
        middle=(lo+hi)/2;row=evaluate(middle)
        if row['residual_pa']==0:lo=hi=middle;left=right=row
        elif row['residual_pa']>0:lo=middle;left=row
        else:hi=middle;right=row
    data,point=operating_network(network,curve,terminal,lo);analysis=calculate(data)
    upper,_=operating_network(network,curve,terminal,hi);upper_analysis=calculate(upper)
    checks=dict(balance=abs(left['residual_pa'])<=curve['pressure_tolerance_pa'],
                flow_bracket=hi-lo<=curve['flow_tolerance_m3_s'],minimum_design_flow=lo>=target['demand_m3_s'],
                velocity_through_bracket=all(s['velocity_pass'] for s in upper_analysis['segments']),
                node_pressure_requirements=all(n['pressure_pass'] for n in analysis['nodes']))
    power=lo*point['total_pressure_rise_pa'];efficiency=point.get('wire_to_water_efficiency')
    electrical=power/efficiency/1000 if efficiency is not None else None
    if not math.isfinite(power) or electrical is not None and not math.isfinite(electrical):raise ProjectError('derived pump power overflowed')
    result.update(status='converged',flow_bracket_m3_s=[lo,hi],checks=checks,calculated_checks_pass=all(checks.values()),
                  operating_point=dict(**left,supply_total_pressure_pa=data['supply']['total_pressure_pa'],
                                       hydraulic_power_kw=power/1000,wire_to_water_efficiency=efficiency,
                                       estimated_electrical_kw=electrical),
                  network_analysis=analysis)
    return result,data


def run(project,curve_path,out):
    import importlib.metadata
    project,curve_path,out=[Path(p).resolve() for p in (project,curve_path,out)]
    if any(out==p or out in p.parents for p in (project,curve_path)):raise ProjectError('output must not contain source inputs')
    before={str(p):digest(p) for p in (project,curve_path)}
    network=json.loads(project.read_text(encoding='utf-8-sig'));curve=json.loads(curve_path.read_text(encoding='utf-8-sig'))
    result,selected=solve(network,curve);out.mkdir(parents=True,exist_ok=False)
    if selected:
        path=out/'operating-network.json';path.write_text(json.dumps(selected,indent=2),encoding='utf-8')
        rerun=analyse(path,out/'analysis')
        if not math.isclose(rerun['supply_flow_m3_s'],result['operating_point']['flow_m3_s'],rel_tol=0,abs_tol=1e-15):raise ProjectError('operating-point rerun flow differs')
        result['selected_rerun_pass']=rerun['calculated_checks_pass']
        result['calculated_checks_pass'] &= result['selected_rerun_pass']
    else:result['selected_rerun_pass']=False
    with (out/'iterations.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(result['trace'][0]));writer.writeheader();writer.writerows(result['trace'])
    result.update(inputs=before,input_roles=dict(network=str(project),curve=str(curve_path)),inputs_unchanged=all(digest(Path(p))==h for p,h in before.items()),curve=curve,network_sources=network['sources'],fluids_version=importlib.metadata.version('fluids'),
                  scope='Single-terminal fixed-pressure boundary, constant-density liquid, supplied fixed-speed piecewise-linear pump curve; fixed route/K',
                  methods=['https://datatool.pumps.org/pump-fundamentals/combined.html','https://datatool.pumps.org/pump-fundamentals/pump-curves',
                           'Existing fluids 1.3.1 Colebrook/laminar pressure engine; source-bounded bisection; P_hydraulic = Q * total pressure rise'])
    if not result['inputs_unchanged']:raise ProjectError('pump/network input changed during analysis')
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Pump operating point</title><h1>Pump operating point</h1><p>'+html.escape(result['scope'])+'</p><p>Design acceptance pending. No curve extrapolation or electrical-project overwrite.</p><pre>'+html.escape(json.dumps({k:result.get(k) for k in ('status','reason','checks','operating_point','flow_bracket_m3_s')},indent=2))+'</pre><h2>Pending</h2><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in result['pending'])+'</ul>',encoding='utf-8')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'pump.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    parser.add_argument('--curve',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();result=run(args.project,args.curve,args.out)
    print(json.dumps({k:result[k] for k in ('status','operating_point','calculated_checks_pass','design_accepted')},indent=2))
    return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
