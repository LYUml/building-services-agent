"""Source-backed steady EPANET 2.2 water graphs via pinned WNTR, in an isolated worker."""
import argparse
import ctypes
import html
import importlib.metadata
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from .cli import digest
from .engine import ProjectError

MODEL='EPANET steady water graph'
PRESSURE='static pressure head in metres of water; head is elevation plus static pressure head'
COORDINATES='schematic diagram coordinates; not physical routes'


def validate(p):
    fields={'model','name','pressure_basis','coordinate_basis','sources','fluid','hydraulics','solver','reservoirs','junctions','pipes','pumps'}
    if not isinstance(p,dict) or set(p)!=fields or p['model']!=MODEL or p['pressure_basis']!=PRESSURE or p['coordinate_basis']!=COORDINATES:
        raise ProjectError('explicit steady water/static-head/schematic-coordinate model required')
    sources=p['sources']
    if not isinstance(p['name'],str) or not p['name'].strip() or not isinstance(sources,dict) or not sources or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip() for k,v in sources.items()):raise ProjectError('network name and source descriptions required')
    def group(row,fields):
        if not isinstance(row,dict) or set(row)!=set(fields)|{'source'} or not isinstance(row['source'],str) or row['source'] not in sources:raise ProjectError('exact sourced water data group required')
    def number(value,minimum=None,positive=False):
        if type(value) not in (int,float) or not math.isfinite(value) or minimum is not None and (value<minimum or positive and value==minimum):raise ProjectError('finite water data within declared domain required')
    group(p['fluid'],{'relative_viscosity','specific_gravity'})
    number(p['fluid']['relative_viscosity'],0,True)
    if p['fluid']['specific_gravity']!=1 or type(p['fluid']['specific_gravity']) not in (int,float):raise ProjectError('this adapter requires explicit water specific gravity 1')
    h=p['hydraulics'];group(h,{'demand_model','minimum_pressure_head_m','required_pressure_head_m','pressure_exponent'})
    if h['demand_model'] not in ('DDA','PDA'):raise ProjectError('explicit DDA or PDA required')
    for key in ('minimum_pressure_head_m','required_pressure_head_m'):number(h[key],0)
    number(h['pressure_exponent'],0,True)
    if h['required_pressure_head_m']<=h['minimum_pressure_head_m']:raise ProjectError('required pressure head must exceed minimum')
    s=p['solver'];group(s,{'max_trials','accuracy','head_tolerance_m','flow_tolerance_m3_s','velocity_tolerance_m_s','mass_tolerance_m3_s','demand_tolerance_m3_s','max_runtime_s'})
    if type(s['max_trials']) is not int or not 1<=s['max_trials']<=10000 or type(s['max_runtime_s']) is not int or not 1<=s['max_runtime_s']<=600:raise ProjectError('explicit bounded engine trial/runtime budgets required')
    for key in ('accuracy','head_tolerance_m','flow_tolerance_m3_s','velocity_tolerance_m_s','mass_tolerance_m3_s','demand_tolerance_m3_s'):number(s[key],0,True)
    nodes={};links={}
    def identity(row,mapped):
        id=row['id']
        if not isinstance(id,str) or re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,30}',id) is None or id in mapped:raise ProjectError('unique EPANET-safe IDs up to 31 ASCII characters required')
        mapped[id]=row
    for kind,keys in [('reservoirs',{'id','head_m','connection_elevation_m','diagram_xy'}),('junctions',{'id','elevation_m','demand_m3_s','diagram_xy','minimum_acceptable_pressure_head_m','minimum_delivered_fraction'})]:
        if not isinstance(p[kind],list) or not p[kind]:raise ProjectError('nonempty reservoir and junction lists required')
        for row in p[kind]:
            group(row,keys);identity(row,nodes)
            if not isinstance(row['diagram_xy'],list) or len(row['diagram_xy'])!=2:raise ProjectError('explicit schematic XY required')
            for v in row['diagram_xy']:number(v)
            if kind=='reservoirs':number(row['head_m']);number(row['connection_elevation_m'])
            else:
                number(row['elevation_m'])
                for key in ('demand_m3_s','minimum_acceptable_pressure_head_m','minimum_delivered_fraction'):number(row[key],0)
                if row['minimum_delivered_fraction']>1:raise ProjectError('delivery target fraction must be <=1')
    if sum(j['demand_m3_s'] for j in p['junctions'])<=0:raise ProjectError('positive total design withdrawal required')
    adjacency={id:set() for id in nodes}
    for kind,keys in [('pipes',{'id','from','to','length_m','diameter_m','roughness_m','minor_k','maximum_velocity_m_s'}),('pumps',{'id','from','to','head_curve'})]:
        if not isinstance(p[kind],list):raise ProjectError('explicit pipe/pump lists required')
        for row in p[kind]:
            group(row,keys);identity(row,links)
            a,b=row['from'],row['to']
            if not isinstance(a,str) or not isinstance(b,str) or a not in nodes or b not in nodes or a==b:raise ProjectError('known distinct water link endpoints required')
            adjacency[a].add(b);adjacency[b].add(a)
            if kind=='pipes':
                for key in ('length_m','diameter_m','maximum_velocity_m_s'):number(row[key],0,True)
                for key in ('roughness_m','minor_k'):number(row[key],0)
                if row['roughness_m']>=row['diameter_m']:raise ProjectError('absolute roughness must be less than diameter')
                z=lambda id:nodes[id].get('elevation_m',nodes[id].get('connection_elevation_m'))
                if row['length_m']+1e-9<abs(z(a)-z(b)):raise ProjectError('pipe route shorter than elevation difference')
            else:
                points=row['head_curve']
                if not isinstance(points,list) or not (len(points)==2 or len(points)>=4) or len(points)>1000:raise ProjectError('two or 4..1000 explicit pump points required; no implicit three-point power-law fit')
                for point in points:
                    if not isinstance(point,list) or len(point)!=2:raise ProjectError('pump points must be flow m3/s, head gain m')
                    number(point[0],0);number(point[1],0,True)
                if points[0][0]!=0 or any(a[0]>=b[0] or a[1]<=b[1] for a,b in zip(points,points[1:])):raise ProjectError('pump curve needs shutoff and strictly increasing flow/decreasing head')
    seen=set();stack=[next(iter(nodes))]
    while stack:
        id=stack.pop()
        if id not in seen:seen.add(id);stack.extend(adjacency[id]-seen)
    if seen!=set(nodes):raise ProjectError('one reservoir-connected graph required; loops/parallel pipes are allowed')
    return p


def build(p):
    import wntr
    wn=wntr.network.WaterNetworkModel();h=p['hydraulics'];s=p['solver'];opts=wn.options.hydraulic
    opts.headloss='D-W';opts.demand_model=h['demand_model'];opts.minimum_pressure=h['minimum_pressure_head_m'];opts.required_pressure=h['required_pressure_head_m'];opts.pressure_exponent=h['pressure_exponent']
    opts.viscosity=p['fluid']['relative_viscosity'];opts.specific_gravity=p['fluid']['specific_gravity'];opts.pattern=None;opts.demand_multiplier=1
    opts.trials=s['max_trials'];opts.accuracy=s['accuracy'];opts.headerror=s['head_tolerance_m'];opts.flowchange=s['flow_tolerance_m3_s'];opts.unbalanced='STOP';opts.inpfile_units='LPS'
    wn.options.time.duration=0;wn.options.quality.parameter='NONE'
    for r in p['reservoirs']:wn.add_reservoir(r['id'],base_head=r['head_m'],coordinates=r['diagram_xy'])
    for j in p['junctions']:wn.add_junction(j['id'],base_demand=j['demand_m3_s'],elevation=j['elevation_m'],coordinates=j['diagram_xy'])
    for link in p['pipes']:wn.add_pipe(link['id'],link['from'],link['to'],length=link['length_m'],diameter=link['diameter_m'],roughness=link['roughness_m'],minor_loss=link['minor_k'],initial_status='OPEN')
    for i,pump in enumerate(p['pumps']):
        curve='C'+str(i);wn.add_curve(curve,'HEAD',pump['head_curve']);wn.add_pump(pump['id'],pump['from'],pump['to'],pump_type='HEAD',pump_parameter=curve,speed=1,initial_status='OPEN')
    return wn


def worker(project,out):
    import wntr
    p=validate(json.loads(Path(project).read_text(encoding='utf-8-sig')));out=Path(out)
    wn=build(p);sim=wntr.sim.EpanetSimulator(wn)
    results=sim.run_sim(file_prefix=str(out/'network'),version=2.2,convergence_error=True)
    version=ctypes.c_int();lib=sim.enData.ENlib;function=getattr(lib,'EN_getversion',None) or lib.ENgetversion
    if function(ctypes.byref(version)) or version.value!=20200:raise ProjectError('verified EPANET 2.2.0 engine required')
    for name,frame in results.node.items():frame.to_csv(out/('node-'+name+'.csv'))
    for name,frame in results.link.items():frame.to_csv(out/('link-'+name+'.csv'))
    raw=dict(nodes={key:{id:float(value) for id,value in frame.loc[0].items()} for key,frame in results.node.items()},
             links={key:{id:float(value) for id,value in frame.loc[0].items()} for key,frame in results.link.items()},
             error_code=results.error_code,engine_codes=list(sim.enData.errcodelist),engine_version=version.value,
             library=str(lib._name),library_sha256=digest(Path(lib._name)),
             versions={name:importlib.metadata.version(name) for name in ('wntr','numpy','scipy','pandas')},
             energy_analysis_performed=False,unused_engine_default_efficiency_percent=wn.options.energy.global_efficiency)
    # Reopen the actual serialized input and check dimensions/demands instead of trusting memory.
    reopened=wntr.network.WaterNetworkModel(str(out/'network.inp'));checks=[]
    close=lambda a,b:math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)
    checks.extend([set(reopened.junction_name_list)=={j['id'] for j in p['junctions']},
                   set(reopened.reservoir_name_list)=={r['id'] for r in p['reservoirs']},
                   set(reopened.pipe_name_list)=={r['id'] for r in p['pipes']},
                   set(reopened.pump_name_list)=={r['id'] for r in p['pumps']},
                   not reopened.tank_name_list,not reopened.valve_name_list,
                   reopened.options.time.duration==0,reopened.options.quality.parameter=='NONE'])
    original=wn.options.hydraulic;actual=reopened.options.hydraulic
    keys=['headloss','demand_model','viscosity','specific_gravity','demand_multiplier','trials','accuracy','headerror','flowchange','unbalanced','inpfile_units']
    # EPANET does not serialize the inactive pressure-demand law for DDA.
    if p['hydraulics']['demand_model']=='PDA':keys+=['minimum_pressure','required_pressure','pressure_exponent']
    for key in keys:
        a,b=getattr(original,key),getattr(actual,key)
        checks.append(close(a,b) if type(a) in (int,float) else a==b)
    for j in p['junctions']:
        node=reopened.get_node(j['id']);checks.extend([close(node.elevation,j['elevation_m']),close(node.base_demand,j['demand_m3_s'])])
    for r in p['reservoirs']:checks.append(close(reopened.get_node(r['id']).base_head,r['head_m']))
    for link in p['pipes']:
        pipe=reopened.get_link(link['id']);checks.extend(close(getattr(pipe,k),link[v]) for k,v in [('length','length_m'),('diameter','diameter_m'),('roughness','roughness_m'),('minor_loss','minor_k')])
        checks.extend([pipe.start_node_name==link['from'],pipe.end_node_name==link['to'],str(pipe.initial_status)=='Open',not pipe.check_valve])
    for i,pump in enumerate(p['pumps']):
        points=reopened.get_curve('C'+str(i)).points
        checks.append(len(points)==len(pump['head_curve']) and all(close(a,c) and close(b,d) for (a,b),(c,d) in zip(points,pump['head_curve'])))
        saved=reopened.get_link(pump['id'])
        checks.extend([saved.start_node_name==pump['from'],saved.end_node_name==pump['to'],saved.pump_type=='HEAD',close(saved.base_speed,1),str(saved.initial_status)=='Open'])
    raw['serialized_input_match']=all(checks)
    (out/'raw.json').write_text(json.dumps(raw,indent=2,allow_nan=False),encoding='utf-8')


def evaluate(p,raw):
    h=p['hydraulics'];s=p['solver'];node=raw['nodes'];link=raw['links'];junctions=[];pipes=[];pumps=[]
    balance={id:-value for id,value in node['demand'].items()}
    for row in p['pipes']+p['pumps']:
        q=link['flowrate'][row['id']];balance[row['from']]-=q;balance[row['to']]+=q
    for j in p['junctions']:
        id=j['id'];pressure=node['pressure'][id];demand=node['demand'][id];target=j['demand_m3_s']
        fraction=1 if h['demand_model']=='DDA' or pressure>=h['required_pressure_head_m'] else 0 if pressure<=h['minimum_pressure_head_m'] else ((pressure-h['minimum_pressure_head_m'])/(h['required_pressure_head_m']-h['minimum_pressure_head_m']))**h['pressure_exponent']
        expected=target*fraction
        junctions.append(dict(id=id,head_m=node['head'][id],static_pressure_head_m=pressure,delivered_m3_s=demand,design_demand_m3_s=target,
            delivered_fraction=demand/target if target else None,mass_residual_m3_s=balance[id],
            head_pressure_identity_pass=abs(node['head'][id]-j['elevation_m']-pressure)<=s['head_tolerance_m'],
            pressure_pass=pressure+s['head_tolerance_m']>=j['minimum_acceptable_pressure_head_m'],
            delivery_pass=demand+s['demand_tolerance_m3_s']>=target*j['minimum_delivered_fraction'],
            demand_law_expected_m3_s=expected,demand_law_pass=abs(demand-expected)<=s['demand_tolerance_m3_s']))
    for pipe in p['pipes']:
        id=pipe['id'];q=link['flowrate'][id];v=abs(q)/(math.pi*pipe['diameter_m']**2/4)
        # Keep raw EPANET velocity and SI Q/A separate. Legacy EPANET LPSperCFS
        # rounding differs from exact cubic-foot conversion; QA has its own sourced tolerance.
        native=link['velocity'][id]
        pipes.append(dict(id=id,flow_m3_s=q,velocity_m_s=v,native_velocity_m_s=native,
                          velocity_difference_m_s=abs(v-native),velocity_pass=v<=pipe['maximum_velocity_m_s'],
                          native_velocity_match=abs(v-native)<=s['velocity_tolerance_m_s']))
    for pump in p['pumps']:
        id=pump['id'];q=link['flowrate'][id];gain=node['head'][pump['to']]-node['head'][pump['from']];expected=None
        for a,b in zip(pump['head_curve'],pump['head_curve'][1:]):
            if a[0]<=q<=b[0]:expected=a[1]+(q-a[0])/(b[0]-a[0])*(b[1]-a[1]);break
        pumps.append(dict(id=id,flow_m3_s=q,head_gain_m=gain,source_curve_head_m=expected,
                          curve_domain_pass=expected is not None,curve_head_pass=expected is not None and abs(gain-expected)<=s['head_tolerance_m'],
                          open_pass=link['status'][id]>0,electrical_power_kw=None))
    finite=all(math.isfinite(v) for group in (node,link) for field in group.values() for v in field.values())
    checks=dict(engine_clean=raw['error_code'] is None and not raw['engine_codes'],serialized_input_match=raw['serialized_input_match'],finite_results=finite,
                mass_balance=all(abs(v)<=s['mass_tolerance_m3_s'] for v in balance.values()),
                head_pressure_identity=all(j['head_pressure_identity_pass'] for j in junctions),demand_law=all(j['demand_law_pass'] for j in junctions),
                pressure_targets=all(j['pressure_pass'] for j in junctions),delivery_targets=all(j['delivery_pass'] for j in junctions),
                velocity_limits=all(r['velocity_pass'] and r['native_velocity_match'] for r in pipes),
                pump_curves=all(r['curve_domain_pass'] and r['curve_head_pass'] and r['open_pass'] for r in pumps))
    return dict(checks=checks,calculated_checks_pass=all(checks.values()),junctions=junctions,pipes=pipes,pumps=pumps,
                reservoir_demands_m3_s={r['id']:node['demand'][r['id']] for r in p['reservoirs']},mass_residuals_m3_s=balance,
                independent_cycle_count=len(p['pipes'])+len(p['pumps'])-len(p['reservoirs'])-len(p['junctions'])+1)


def run(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    if out==project or out in project.parents:raise ProjectError('output must not contain source water data')
    before=digest(project);p=validate(json.loads(project.read_text(encoding='utf-8-sig')))
    if importlib.metadata.version('wntr')!='1.5.0':raise ProjectError('pinned WNTR 1.5.0 required')
    out.mkdir(parents=True,exist_ok=False);copied=out/'source-copy.json';copied.write_bytes(project.read_bytes())
    result=dict(calculated_checks_pass=False,design_accepted=False,scope='Steady EPANET 2.2 water graph, D-W friction, fixed head sources and fixed-speed sourced head curves; static pressure head only',
                pending=['source fluid/roughness/demand and device-curve applicability','BIM/route binding, independent general pipe energy residuals and physical acceptance',
                         'pump efficiency/power, NPSH, controls, tanks/time variation and water quality','domain-specific water/fire rules and full engineering acceptance'])
    with (out/'worker.log').open('wb') as log:
        try:
            process=subprocess.run([sys.executable,'-m','bsa.epanet','_worker',str(copied),'--out',str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=p['solver']['max_runtime_s'])
            if process.returncode:raise ProjectError('EPANET worker failed; inspect worker.log and native INP/RPT artifacts')
            raw=json.loads((out/'raw.json').read_text());result.update(evaluate(p,raw),runtime={k:raw[k] for k in ('engine_version','library','library_sha256','versions','engine_codes','error_code','energy_analysis_performed','unused_engine_default_efficiency_percent')})
        except (subprocess.TimeoutExpired,ProjectError,ValueError,KeyError,OSError) as exc:result['engine_error']=str(exc)
    result.update(input_sha256=before,input_unchanged=digest(project)==before,source_data=p)
    if not result['input_unchanged']:raise ProjectError('source water input changed')
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>EPANET water graph</title><h1>EPANET water graph</h1><p>'+html.escape(result['scope'])+'</p><p>Static head m; not total pressure Pa. Pump power and default efficiency are not accepted design data.</p><pre>'+html.escape(json.dumps({k:result.get(k) for k in ('engine_error','checks','junctions','pipes','pumps')},indent=2))+'</pre><h2>Pending</h2><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in result['pending'])+'</ul>',encoding='utf-8')
    result['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
    (out/'water.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project');parser.add_argument('worker_project',nargs='?');parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    if args.project=='_worker':worker(args.worker_project,args.out);return 0
    result=run(args.project,args.out);print(json.dumps({k:result.get(k) for k in ('checks','engine_error','calculated_checks_pass','design_accepted')},indent=2));return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
