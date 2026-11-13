"""Finite supplied elbow-radius selection using pinned SciPy/HiGHS MILP."""
import argparse
import importlib.metadata
import json
import math
import tempfile
from pathlib import Path
from . import duct_elbow_backbone as author
from .cli import digest
from .workspace import allowed


def runtime():
    import scipy.optimize._highspy._core as core
    from scipy.optimize import milp
    versions={k:importlib.metadata.version(k) for k in ('scipy','numpy')}
    if versions!={'scipy':'1.18.1','numpy':'2.5.4'}:raise ValueError('Pinned SciPy/NumPy runtime required')
    from . import duct_backbone_ifc,duct_system_paths,duct_equivalent,workspace
    modules=[author,author.bim,author.straight,author.elbow,author.circular_geometry,duct_backbone_ifc,duct_system_paths,duct_equivalent,workspace]
    return versions,{str(p.resolve()):digest(p) for p in [Path(core.__file__),Path(milp.__code__.co_filename),Path(__file__),*[Path(m.__file__) for m in modules]]}


def number(value,positive=False):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0 or positive and value==0:raise ValueError('Finite nonnegative quantities required')
    return value


def calculate(junction,schedule,basis,policy):
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    versions,_=runtime()
    if not isinstance(policy,dict) or set(policy)!={'basis','minimum_remainder_m','nodes'} or not isinstance(policy['basis'],str) or not policy['basis'].strip():raise ValueError('Exact supplied radius policy required')
    minimum=policy['minimum_remainder_m']
    if set(minimum)!={'value','classification','source'} or minimum['classification'] not in ('assumed','design_target') or not isinstance(minimum['source'],str) or not minimum['source'].strip():raise ValueError('Explicit geometric remainder design target required')
    reserve=number(minimum['value'],True)
    nodes={n['node']:n for n in junction['nodes']};wanted=sorted(n for n in nodes if nodes[n]['connection_requirement']=='elbow_required')
    if not wanted or set(policy['nodes'])!=set(wanted):raise ValueError('Every source equal-section elbow needs explicit candidates')
    # Existing source compiler validates topology, source friction and dimensions first.
    author.source_model(junction,schedule,basis)
    thickness=basis['wall_thickness_m']['value'];variables=[];screen=[]
    for name in wanted:
        rows=policy['nodes'][name];seen=set()
        if not isinstance(rows,list) or not rows:raise ValueError('Nonempty finite candidate lists required')
        for row in rows:
            if set(row)!={'id','radius_m','penalty','classification','source'} or not isinstance(row['id'],str) or not row['id'].strip() or row['id'] in seen or row['classification'] not in ('assumed','design_target','given','measured') or not isinstance(row['source'],str) or not row['source'].strip():raise ValueError('Unique sourced classified candidates required')
            seen.add(row['id']);radius=number(row['radius_m'],True);number(row['penalty'])
            eligible=radius>(nodes[name]['incidents'][0]['width_m']+2*thickness)/2
            screen.append(dict(node=name,**row,geometry_eligible=eligible))
            if eligible:variables.append((name,row))
    if len(screen)>256:raise ValueError('At most 256 supplied radius candidates supported')
    result=dict(status='no_feasible_candidate',screening=screen,selected=None,selected_radii=None,objective=None,versions=versions,policy=policy,design_accepted=False,scope='Finite supplied geometric radius/known-elbow trim selection only; other fitting trims, products, installed scale, full pressure and complete design remain unresolved')
    if any(not any(n==name for n,_ in variables) for name in wanted):return result
    matrix=[];lower=[];upper=[]
    for name in wanted:matrix.append([int(n==name) for n,_ in variables]);lower.append(1);upper.append(1)
    budgets=[]
    for edge in schedule['flow_aggregation']['sections']:
        ends=[edge['from'],edge['to']];length=math.dist(nodes[ends[0]]['point_m'],nodes[ends[1]]['point_m'])
        if any(n in wanted for n in ends):
            matrix.append([row['radius_m'] if name in ends else 0 for name,row in variables]);lower.append(-np.inf);upper.append(length-reserve)
        budgets.append(dict(section=edge['id'],source_centreline_m=length,elbow_nodes=[n for n in ends if n in wanted]))
    solved=milp(np.array([r['penalty'] for _,r in variables]),integrality=np.ones(len(variables)),bounds=Bounds(0,1),constraints=LinearConstraint(np.array(matrix,dtype=float),lower,upper),options={'mip_rel_gap':0.0})
    result['solver_status']=int(solved.status);result['source_budgets']=budgets
    if solved.status==2:return result
    if solved.status!=0 or solved.x is None:raise ValueError('MILP did not prove an optimum')
    if any(abs(v-round(v))>1e-7 for v in solved.x):raise ValueError('MILP result is not integral')
    selected={name:dict(row) for (name,row),v in zip(variables,solved.x) if v>.5}
    if set(selected)!=set(wanted) or sum(v>.5 for v in solved.x)!=len(wanted):raise ValueError('Exact one candidate per elbow required')
    radii={n:{k:r[k] for k in ('radius_m','classification','source')} for n,r in selected.items()}
    _,fit=author.compile_model(junction,schedule,basis,radii)
    if fit['blocked_elbow_nodes']:raise ValueError('Selected radii fail independent source fit replay')
    for row in fit['source_section_budgets']:
        if row['declared_elbow_trims_m'] and row['remaining_after_declared_elbows_m']<reserve-1e-8:raise ValueError('Selected two-end remainder violates policy')
    cost=math.fsum(r['penalty'] for r in selected.values())
    if not math.isclose(cost,float(solved.fun),rel_tol=1e-10,abs_tol=1e-8):raise ValueError('Selected objective differs')
    result.update(status='candidate_selected',selected=selected,selected_radii=radii,objective=cost,fit=fit)
    return result


def run(plan,workflow,native_task,basis,policy,out):
    from .duct_junction_review import from_workflow
    paths=[Path(p).resolve() for p in (plan,workflow,basis,policy,out)];plan,workflow,basis,policy,out=paths
    if not all(allowed(p) for p in paths) or out.exists() or any(out==p or out in p.parents for p in paths[:-1]) or out.is_relative_to(workflow):raise ValueError('Fresh selected project output separate from sources required')
    versions,methods=runtime();pins={str(p):digest(p) for p in (plan,workflow/'workflow.json',basis,policy)}|methods
    junction=from_workflow(plan,workflow,native_task,out/'junction.json');schedule=workflow/junction['lineage'][-1]/'results.json';pins[str(schedule)]=digest(schedule);pins.update(junction['inputs'])
    result=calculate(junction,json.loads(schedule.read_text()),json.loads(basis.read_text()),json.loads(policy.read_text()))
    result.update(inputs=pins,source=dict(plan=str(plan),workflow=str(workflow),native_task=native_task,basis=str(basis),policy=str(policy),schedule=str(schedule)))
    if result['selected_radii'] is not None:
        radii=out/'selected-radii.json';radii.write_text(json.dumps(result['selected_radii'],indent=2))
        native=author.run(plan,workflow,native_task,basis,radii,out/'native');result['native_saved_checks']=native['saved_checks']
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Selection source or runtime changed')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'selection.json').write_text(json.dumps(result,indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    result=json.loads((out/'selection.json').read_text());source=result['source']
    if result['design_accepted'] is not False or any(digest(Path(p))!=sha for p,sha in result['inputs'].items()):raise ValueError('Selection source or method changed')
    for name,sha in result['artifacts'].items():
        p=(out/name).resolve()
        if not p.is_relative_to(out) or digest(p)!=sha:raise ValueError('Selection artifact differs')
    from .workflow import verify as verify_workflow
    if not verify_workflow(Path(source['workflow']))['integrity_pass']:raise ValueError('Original source workflow changed')
    from .duct_junction_review import from_workflow
    if not all(allowed(Path(source[k])) for k in ('plan','workflow','basis','policy','schedule')):raise ValueError('Original selected project sources required')
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='radius-audit-') as folder:
        junction=from_workflow(source['plan'],source['workflow'],source['native_task'],Path(folder)/'junction.json')
    if junction!=json.loads((out/'junction.json').read_text()):raise ValueError('Saved junction differs from original native source')
    schedule=Path(source['workflow'])/junction['lineage'][-1]/'results.json'
    if schedule!=Path(source['schedule']):raise ValueError('Selected schedule ancestry differs')
    _,methods=runtime()
    wanted={str(Path(p).resolve()):digest(Path(p)) for p in (source['plan'],str(Path(source['workflow'])/'workflow.json'),source['basis'],source['policy'],str(schedule))}|methods|junction['inputs']
    if wanted!=result['inputs']:raise ValueError('Selection input inventory differs from original source')
    fresh=calculate(junction,json.loads(schedule.read_text()),json.loads(Path(source['basis']).read_text()),json.loads(Path(source['policy']).read_text()))
    if any(result.get(k)!=v for k,v in fresh.items()):raise ValueError('Radius selection differs from source replay')
    if fresh['selected_radii'] is not None:
        model,fit=author.compile_model(json.loads((out/'junction.json').read_text()),json.loads(Path(source['schedule']).read_text()),json.loads(Path(source['basis']).read_text()),fresh['selected_radii'])
        if model!=json.loads((out/'native/model-input.json').read_text()) or fit!=fresh['fit']:raise ValueError('Native model differs from selected source radii')
        checked=author.inspect_saved(out/'native/Supply Backbone.ifc',model)
        if result.get('native_saved_checks')!=checked:raise ValueError('Saved native checks differ')
    elif (out/'native').exists() or (out/'selected-radii.json').exists():raise ValueError('Infeasible selection cannot author native geometry')
    return dict(integrity_pass=True,status=fresh['status'],selected_elbows=len(fresh['selected_radii'] or {}),design_accepted=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);v=s.add_parser('verify');v.add_argument('out');r=s.add_parser('run')
    for n in ('plan','workflow','native_task','basis','policy'):r.add_argument(n)
    r.add_argument('--out',required=True);a=p.parse_args()
    result=verify(a.out) if a.command=='verify' else run(a.plan,a.workflow,a.native_task,a.basis,a.policy,a.out)
    print(json.dumps({k:result[k] for k in ('status','design_accepted')},indent=2))
    return 0 if result['status']=='candidate_selected' else 2

if __name__=='__main__':raise SystemExit(main())
