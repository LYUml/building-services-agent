"""Separate, conditional manufacturer-curve comparison; never an ADPI acceptance engine."""
import argparse
import csv
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

from fluids.numerics import interp
from pypdf import PdfReader
from shapely import union_all
from shapely.geometry import Point,LineString,box,mapping,shape
from .air_allocation import prepare
from .terminal_performance import calculate as performance
from .autocad_source import local
from .cli import digest
from .workspace import ROOT
from .workflow import verify as verify_workflow

PERFORMANCE_SHA='073c639219b28068a0c8190a926d493e42a12c0918db464ee8439c55a3994aef'
CURVE_SHA='f98aa9ded59150e157c83d5c5114faaa1a24c185928709ffe5d60c9b2f607988'
SCOPE='Paired published-load curve diagnostic at fixed inherited thermal/airflow assumptions; not interpolation to actual room load, measured ADPI, installed layout or engineering acceptance'


def catalogue(pdf):
    if digest(pdf)!=PERFORMANCE_SHA:raise ValueError('Exact visually reviewed performance source required')
    text=PdfReader(pdf).pages[1].extract_text()
    if '600x600mm PANEL (NO DAMPER)' not in text:raise ValueError('Selected panel/damper source differs')
    rows=[]
    for line in text.splitlines():
        parts=re.sub(r'^(?:(6|8|10|12|14|15)[\u201d"]|Dia\.)\s+','',line.strip()).split()
        if len(parts)!=25 or any(parts[i]!='-' for i in (5,7,15,17)):continue
        try:
            q,pt,ps,t=map(float,[parts[i] for i in (11,12,13,18)])
            nc=None if parts[9]=='-' else float(parts[9])
            if float(parts[0])<=0:continue
        except ValueError:continue
        rows.append(dict(flow_L_s=q,total_pressure_Pa=pt,static_pressure_Pa=ps,T025_m=t,NC=nc,NC_qualifier='less than 10' if nc is None else 'catalogue value'))
    if len(rows)!=54:raise ValueError('Exact six nine-row neck tables required')
    result={str(neck):rows[i*9:(i+1)*9] for i,neck in enumerate((6,8,10,12,14,15))}
    if [result[k][0]['flow_L_s'] for k in result]!=[37,33,51,74,101,116]:raise ValueError('Published neck/flow association differs')
    return result


def curve_value(curves,load,x):
    for fragment in curves['fragments']:
        pts=fragment['points']
        if fragment['load_Btuh_ft2']==load and pts[0][0]<=x<=pts[-1][0]:
            return interp(x,[p[0] for p in pts],[p[1] for p in pts])
    return None


def screen(curves,load,x,target=80):
    delta=curves['stroke_width_ratio'];ys=[curve_value(curves,load,v) for v in (x-delta,x,x+delta)]
    if any(v is None for v in ys):return dict(status='outside_published_curve_or_fragment_domain',ratio=x,represented_ADPI=None)
    lower=min(ys)-curves['stroke_width_ADPI_points']
    return dict(status='paired_curve_threshold_met' if lower>=target else 'below_paired_curve_threshold',ratio=x,
                represented_ADPI=ys[1],stroke_margin_lower_ADPI=lower)


def lengths(boundary,terminals):
    result={};extent=2*math.hypot(boundary.bounds[2]-boundary.bounds[0],boundary.bounds[3]-boundary.bounds[1])
    for t in terminals:
        p=t['center_m'];values={}
        for name,(dx,dy) in dict(east=(1,0),west=(-1,0),north=(0,1),south=(0,-1)).items():
            ray=boundary.intersection(LineString([p,[p[0]+dx*extent,p[1]+dy*extent]]))
            pieces=list(ray.geoms) if hasattr(ray,'geoms') else [ray]
            connected=[g for g in pieces if g.geom_type=='LineString' and g.distance(Point(p))<1e-8]
            if len(connected)!=1:raise ValueError('Unambiguous source boundary ray required')
            distance=max((x-p[0])*dx+(y-p[1])*dy for x,y in connected[0].coords)
            for other in terminals:
                v=other['center_m'];along=(v[0]-p[0])*dx+(v[1]-p[1])*dy;perpendicular=(v[0]-p[0])*dy-(v[1]-p[1])*dx
                if other['id']!=t['id'] and abs(perpendicular)<1e-8 and along>1e-8:distance=min(distance,along/2)
            if distance<=0:raise ValueError('Positive diagnostic characteristic length required')
            values[name]=distance
        result[t['id']]=values
    return result


def grid(boundary,split_y,shape_pair):
    x0,y0,x1,y1=boundary.bounds;points=[]
    for zone,(nx,ny),lo,hi in zip(('main','bay'),shape_pair,(y0,split_y),(split_y,y1)):
        region=boundary.intersection(box(x0,lo,x1,hi))
        pieces=list(region.geoms) if hasattr(region,'geoms') else [region]
        region=union_all([g for g in pieces if g.area>0]);a,b,c,d=region.bounds
        for ix in range(nx):
            for iy in range(ny):
                cell=region.intersection(box(a+(c-a)*ix/nx,b+(d-b)*iy/ny,a+(c-a)*(ix+1)/nx,b+(d-b)*(iy+1)/ny))
                if cell.is_empty or cell.area<=0:raise ValueError('Empty sampled grid cell')
                p=cell.representative_point();points.append(dict(id=f'{zone}-{ix+1}-{iy+1}',center_m=[p.x,p.y]))
    return points


def evaluate(allocation,directions,tables,curves):
    attempts=[]
    for neck,rows in tables.items():
        failures=[];cases=0;minimum_margin=math.inf
        for t in allocation['terminals']:
            for condition,q,loads in [('maximum',t['maximum_flow_L_s'],(40,60)),('minimum',t['minimum_flow_L_s'],(20,40))]:
                value=performance(rows,q)
                if value['status']!='within_catalogue':
                    failures.append(dict(terminal=t['id'],condition=condition,reason='outside_original_performance_table',flow_L_s=q));continue
                for direction,length in directions[t['id']].items():
                    ratio=value['T025_m']/length
                    for load in loads:
                        cases+=1;reading=screen(curves,load,ratio)
                        if reading.get('stroke_margin_lower_ADPI') is not None:minimum_margin=min(minimum_margin,reading['stroke_margin_lower_ADPI']-80)
                        if reading['status']!='paired_curve_threshold_met':failures.append(dict(terminal=t['id'],condition=condition,direction=direction,load_Btuh_ft2=load,reason=reading['status'],ratio=ratio,flow_L_s=q))
        reasons={}
        for f in failures:reasons[f['reason']]=reasons.get(f['reason'],0)+1
        attempts.append(dict(neck_inch=int(neck),terminal_count=len(allocation['terminals']),evaluated_curve_cases=cases,
            status='conditional_candidate' if not failures else 'rejected',failure_count=len(failures),failure_reason_counts=reasons,
            minimum_represented_threshold_margin=None if math.isinf(minimum_margin) else minimum_margin,failures=failures))
    return attempts


def square_grid_envelope(tables,curves,turndown,density,specific_heat,temperature_difference):
    """Optimistic necessary bound for a regular square interior grid only."""
    if type(turndown) not in (int,float) or not 0<turndown<=1:raise ValueError('Positive turndown required')
    for value in (density,specific_heat,temperature_difference):
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('Positive finite inherited air/temperature values required')
    limits=[]
    level=80+curves['stroke_width_ADPI_points']
    for load in (40,60):
        supported=[]
        for fragment in curves['fragments']:
            if fragment['load_Btuh_ft2']!=load:continue
            for a,b in zip(fragment['points'],fragment['points'][1:]):
                if a[1]>=level:supported.append(a[0])
                if b[1]>=level:supported.append(b[0])
                if (a[1]-level)*(b[1]-level)<0:
                    supported.append(a[0]+(b[0]-a[0])*(level-a[1])/(b[1]-a[1]))
        if not supported:raise ValueError('Paired curve has no represented threshold support')
        limits.append(max(supported)-curves['stroke_width_ratio'])
    ratio_max=min(limits)
    if ratio_max<=0:raise ValueError('Positive represented ratio bound required')
    results=[]
    for neck,rows in tables.items():
        low=rows[0]['flow_L_s']/turndown;high=rows[-1]['flow_L_s']
        if low>high:
            results.append(dict(neck_inch=int(neck),status='no_simultaneous_catalogue_flow_domain'));continue
        candidates=[low,high]
        # Exact extrema of q/(a*q+b)^2 on each original piecewise-linear throw segment.
        for a,b in zip(rows,rows[1:]):
            qa,qb=a['flow_L_s'],b['flow_L_s'];slope=(b['T025_m']-a['T025_m'])/(qb-qa);intercept=a['T025_m']-slope*qa
            candidates.extend(q for q in (qa,qb) if low<=q<=high)
            if slope:
                q=intercept/slope
                if max(low,qa)<=q<=min(high,qb):candidates.append(q)
        def at(q):
            throw=interp(q,[r['flow_L_s'] for r in rows],[r['T025_m'] for r in rows])
            length=throw/ratio_max;air_density=q/(4*length*length)
            return dict(flow_L_s=q,minimum_required_L_m=length,airflow_density_L_s_m2=air_density,
                conditional_sensible_W_m2=air_density/1000*density*specific_heat*temperature_difference)
        best=max((at(q) for q in candidates),key=lambda v:v['airflow_density_L_s_m2'])
        results.append(dict(neck_inch=int(neck),status='necessary_bound_only',**best))
    return dict(maximum_paired_curve_ratio=ratio_max,neck_bounds=results,
        scope='Optimistic necessary bound for regular square interior grid: spacing=2L, area=4L². Maximizes q/area across original catalogue segments with both operating flows in range. Ignores lower ratio limit and minimum-load curve test; not a sufficient design, arbitrary-layout bound or measured comfort prediction.',
        actual_room_load_verified=False,ADPI_verified=False,design_accepted=False)


def run(plan,workflow,curves_dir,performance_pdf,policy,output,pdf2plot_python):
    plan,workflow,curves_dir,performance_pdf,policy,output=map(local,(plan,workflow,curves_dir,performance_pdf,policy,output))
    if output.exists() or any(output==p or output in p.parents or p.is_dir() and p in output.parents for p in (plan,workflow,curves_dir,performance_pdf,policy)):raise ValueError('Fresh separate project output required')
    if not verify_workflow(workflow)['integrity_pass']:raise ValueError('Existing workflow source changed')
    saved=json.loads((workflow/'workflow.json').read_text(encoding='utf-8'))
    if saved['inputs'].get(str(plan))!=digest(plan):raise ValueError('Wrong source plan')
    tasks={t['id']:t for t in json.loads(plan.read_text(encoding='utf-8'))['tasks']}
    producers=[t for t in tasks.values() if t['kind']=='air_allocation' and saved['tasks'][t['id']]['status']=='pass']
    if len(producers)!=1:raise ValueError('One passing source allocation required')
    task=producers[0];source_project=local(plan.parent/task['project']);p=json.loads(source_project.read_text(encoding='utf-8'))
    boundary_path=local(source_project.parent/p['boundary'])
    if digest(boundary_path)!=p['boundary_sha256']:raise ValueError('Original boundary changed')
    boundary=shape(json.loads(boundary_path.read_text(encoding='utf-8')))
    original=json.loads((workflow/task['id']/'allocation.json').read_text(encoding='utf-8'))
    spec=json.loads(policy.read_text(encoding='utf-8'))
    if set(spec)!={'grids','split_y_m','basis','classification','curve_document'} or spec['classification']!='design_choice' or not spec['basis'].strip():raise ValueError('Explicit bounded scenario policy required')
    grids=spec['grids']
    if not grids or len(grids)>20 or any(len(pair)!=2 or any(len(g)!=2 or any(type(v)is not int or v<1 for v in g) for g in pair) or sum(g[0]*g[1] for g in pair)>160 for pair in grids):raise ValueError('Bounded two-zone grid policy required')
    curve_pdf=local(policy.parent/spec['curve_document'])
    if digest(curve_pdf)!=CURVE_SHA:raise ValueError('Original manufacturer curve document changed')
    curves=json.loads((curves_dir/'curves.json').read_text(encoding='utf-8'))
    if curves['source_pdf_sha256']!=CURVE_SHA or curves['ADPI_verified'] is not False:raise ValueError('Unaccepted source-bound curve extraction required')
    runtime=Path(pdf2plot_python).resolve();worker=ROOT/'scripts/extract_krueger_adpi.py'
    if not runtime.is_file():raise ValueError('Explicit isolated PDF runtime required')
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='adpi-source-replay-') as temp:
        folder=Path(temp)/'curves'
        process=subprocess.run([str(runtime),str(worker),str(curve_pdf),'--out',str(folder)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        if process.returncode or json.loads((folder/'curves.json').read_text(encoding='utf-8'))!=curves:raise ValueError('Saved curve data differs from actual source/helper replay')
    maximum_load=original['load']['sensible_trial_kW_thermal']*1000/original['load']['inputs']['area']['value']
    minimum_load=maximum_load*original['turndown']
    W_M2_PER_BTUH_FT2=1055.05585262/3600/(.3048**2)
    if not 40<maximum_load/W_M2_PER_BTUH_FT2<60 or not 20<minimum_load/W_M2_PER_BTUH_FT2<40:raise ValueError('Inherited conditional loads are outside the selected paired-curve brackets')
    tables=catalogue(performance_pdf)
    pins={str(path):digest(path) for path in [plan,workflow/'workflow.json',source_project,boundary_path,workflow/task['id']/'allocation.json',performance_pdf,policy,curve_pdf,curves_dir/'curves.json',Path(__file__),runtime,worker,ROOT/'scripts/extract_tcf_vectors.py',ROOT/'tools/pdf2plot-99a8ee1/pdf2plot_helper.py']}
    scenarios=[]
    for name,points in [('original-80',p['terminals'])]+[(f'grid-{idx+1}',grid(boundary,spec['split_y_m'],pair)) for idx,pair in enumerate(grids)]:
        allocation=prepare(mapping(boundary),points,p['load_inputs'],p['turndown'])
        if allocation['load']!=original['load']:raise ValueError('Comparison replaced original thermal/airflow balance')
        directions=lengths(boundary,points)
        attempts=evaluate(allocation,directions,tables,curves)
        scenarios.append(dict(id=name,terminal_count=len(points),total_supply_L_s=allocation['load']['supply_flow_L_s'],
            terminals=points,diagnostic_lengths_m=directions,neck_attempts=attempts))
    if any(digest(Path(path))!=sha for path,sha in pins.items()):raise ValueError('Source changed during comparison')
    candidates=[dict(scenario=s['id'],neck=a['neck_inch']) for s in scenarios for a in s['neck_attempts'] if a['status']=='conditional_candidate']
    for scenario in scenarios:
        options={t['id']:[] for t in scenario['terminals']}
        for attempt in scenario['neck_attempts']:
            failed={f['terminal'] for f in attempt['failures']}
            for terminal in set(options)-failed:options[terminal].append(attempt['neck_inch'])
        scenario['mixed_neck_options']=options
        scenario['mixed_neck_covered_terminals']=sum(bool(v) for v in options.values())
        scenario['mixed_neck_whole_layout_candidate']=all(options.values())
    air=p['load_inputs']
    envelope=square_grid_envelope(tables,curves,p['turndown'],air['density']['value'],air['specific_heat']['value'],air['temperature_difference']['value'])
    result=dict(plan=str(plan),workflow=str(workflow),curves=str(curves_dir),performance_pdf=str(performance_pdf),policy=str(policy),pdf2plot_python=str(runtime),inputs=pins,versions={k:importlib.metadata.version(k) for k in ('ezdxf','shapely','fluids','pypdf')},scenarios=scenarios,
        scenario_count=len(scenarios),neck_comparisons=len(scenarios)*len(tables),conditional_candidates=candidates,status='conditional_candidates' if candidates else 'no_feasible_sampled_candidate',
        regular_square_grid_necessary_envelope=envelope,
        load_assumptions=dict(maximum_sensible_W_m2=maximum_load,minimum_sensible_W_m2=minimum_load,W_m2_per_Btuh_ft2=W_M2_PER_BTUH_FT2,minimum_load_basis='Declared constant-temperature-difference scenario: inherited 40% flow corresponds to 40% sensible load; actual part-load room load unverified',maximum_source_curves_Btuh_ft2=[40,60],minimum_source_curves_Btuh_ft2=[20,40],interpolation_between_loads=False),
        scope=SCOPE,lengths_scope='Actual polygon wall-ray and exactly aligned opposing-midplane diagnostic proxies; physical wall/jet/ceiling applicability remains unknown',
        source_curve_margin_scope='Full source stroke-width margin in both axes; not source testing/measurement/installation uncertainty',
        ADPI_verified=False,design_accepted=False)
    output.mkdir(parents=True);(output/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (output/'comparison.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['Scenario','Terminals','Neck inch','Status','Failure count'])
        for s in scenarios:
            for a in s['neck_attempts']:writer.writerow([s['id'],s['terminal_count'],a['neck_inch'],a['status'],a['failure_count']])
    return result


def verify(output):
    output=local(output);saved=json.loads((output/'comparison.json').read_text(encoding='utf-8'))
    if any(digest(Path(p))!=sha for p,sha in saved['inputs'].items()):raise ValueError('Comparison source/method changed')
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='adpi-comparison-replay-') as temp:
        fresh=run(*[saved[k] for k in ('plan','workflow','curves','performance_pdf','policy')],Path(temp)/'comparison',saved['pdf2plot_python'])
        if fresh!=saved:raise ValueError('Saved comparison differs from independent source/geometry/calculation replay')
        if (Path(temp)/'comparison/comparison.csv').read_bytes()!=(output/'comparison.csv').read_bytes():raise ValueError('Comparison CSV differs from reconstructed rows')
    return dict(integrity_pass=True,status=saved['status'],scenario_count=saved['scenario_count'],neck_comparisons=saved['neck_comparisons'],ADPI_verified=False,design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True);q=sub.add_parser('run')
    for name in ('plan','workflow','curves','performance_pdf','policy'):q.add_argument(name)
    q.add_argument('--out',required=True);q.add_argument('--pdf2plot-python',required=True)
    sub.add_parser('verify').add_argument('output');a=p.parse_args()
    r=verify(a.output) if a.command=='verify' else run(a.plan,a.workflow,a.curves,a.performance_pdf,a.policy,a.out,a.pdf2plot_python)
    print(json.dumps({k:r[k] for k in ('status','scenario_count','neck_comparisons','ADPI_verified')}))
