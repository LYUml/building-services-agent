"""Execute one source-bound terminal design iteration through existing engines."""
import argparse
import json
import os
from pathlib import Path
from .cli import digest
from .workspace import allowed
from . import delivery,spatial_terminal_search as search,spatial_terminal_candidate_plan as candidate_plan
from . import workflow,workflow_status,modules
from .workflow_modules import host_selection,parse_provider_options

OPTIONS={'energyplus','autocad','radiance_bin','ifcmcp_python','three_phase_python','graphviz','pdf2plot_python','honeybee_python','module_providers','module_runtime','disabled_module_providers'}
SCOPE='One bounded terminal candidate iteration from an existing source-bound workflow; not semantic raw-brief design, automatic physical repair or complete engineering acceptance'


def stage_order(stages):
    values=dict(search={'candidate_available','no_feasible_candidate'},plan={'materialized_verified'},requirements={'completed','failed','unavailable','pending'},workflow={'executed'},diagnosis={'source_verified'})
    if not isinstance(stages,dict) or set(stages)-set(values) or any(not isinstance(value,str) or value not in values[key] for key,value in stages.items()):raise ValueError('Supported exact iteration stages required')
    for child,parent,required in [('plan','search','candidate_available'),('requirements','plan','materialized_verified'),('workflow','requirements','completed'),('diagnosis','workflow','executed')]:
        if child in stages and stages.get(parent)!=required:raise ValueError('Iteration released incomplete prerequisites')


def search_link(studied,original,policy):
    if studied['original']!=str(original) or studied['policy']!=str(policy):raise ValueError('Iteration search replaced declared original/policy')


def needs_geometry(tasks,selected):
    chain={selected}
    for task in tasks:
        if task.get('depends_on') in chain:
            chain.add(task['id'])
            if task['kind'] in ('spatial_terminal_ifc','spatial_terminal_inlets','spatial_terminal_stubs'):return True
    return False


def input_pins(plan,original_run,policy,geometry_policy,report,original):
    files={plan,original_run/'workflow.json',policy,original}
    if geometry_policy is not None:files.add(geometry_policy)
    pins=dict(report['inputs']);pins.update({str(original_run/name):sha for name,sha in report['artifact_hashes'].items()})
    for p in files:
        sha=digest(p)
        if str(p) in pins and pins[str(p)]!=sha:raise ValueError('Original snapshot changed before iteration')
        pins[str(p)]=sha
    for module in (delivery,search,candidate_plan,workflow,workflow_status,modules):
        p=Path(module.__file__).resolve();sha=digest(p)
        if str(p) in pins and pins[str(p)]!=sha:raise ValueError('Original method changed before iteration')
        pins[str(p)]=sha
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return pins


def run(plan,original_run,task,policy,target,out,*,geometry_policy=None,execute_options=None):
    plan,original_run,policy,target,out=[Path(p).resolve() for p in (plan,original_run,policy,target,out)]
    geometry_policy=Path(geometry_policy).resolve() if geometry_policy is not None else None
    if not all(allowed(p) for p in (plan,original_run,policy,target,out)) or geometry_policy is not None and not allowed(geometry_policy):raise ValueError('Explicit selected project paths required')
    target_inputs=target.parent/(target.stem+'-inputs');manifest=target.with_suffix('.provenance.json')
    if target.parent!=plan.parent or target.suffix!='.json' or any(p.exists() for p in (target,target_inputs,manifest,out)):raise ValueError('Fresh separate iteration output and same-directory target plan required')
    if out.is_relative_to(original_run) or original_run.is_relative_to(out) or target.is_relative_to(original_run) or target_inputs.is_relative_to(out) or out.is_relative_to(target_inputs):raise ValueError('Iteration must preserve original run and separate plan inputs')
    options={} if execute_options is None else dict(execute_options)
    if set(options)-OPTIONS:raise ValueError('Supported explicit host runtime options required')
    source,report,integrity=delivery.context(plan,original_run)
    if not integrity['integrity_pass']:raise ValueError('Original workflow evidence is stale')
    tasks={t['id']:t for t in source['tasks']}
    if task not in tasks or tasks[task]['kind']!='spatial_terminal_performance':raise ValueError('Explicit original spatial terminal performance task required')
    selection=host_selection(source['tasks'],options.get('module_providers'),options.get('disabled_module_providers',()))
    original=original_run/task/'terminal-performance.json'
    files={plan,original_run/'workflow.json',policy,original}
    if geometry_policy is not None:files.add(geometry_policy)
    if any(out==p or out in p.parents for p in files):raise ValueError('Iteration output overlaps source')
    pins=input_pins(plan,original_run,policy,geometry_policy,report,original)
    out.mkdir(parents=True)
    result=dict(schema='bsa.terminal-iteration/1',original_plan=str(plan),original_run=str(original_run),performance_task=task,target_plan=str(target),search_policy=str(policy),geometry_policy=str(geometry_policy) if geometry_policy else None,
        inputs=pins,module_selection=selection,status='not_executed',stages={},original_requirements=source['requirements'],original_unresolved_inputs=source.get('unresolved_inputs',[]),actions=[],engineering_actions=[],stage_errors={},design_accepted=False,
        scope=SCOPE)
    stage='search'
    try:
        studied=search.run(original,policy,out/'search');search.verify(out/'search');result['stages']['search']=studied['proposal']['status']
        if studied['proposal']['status']!='candidate_available':result['status']='no_feasible_candidate'
        elif needs_geometry(source['tasks'],task) and geometry_policy is None:result['status']='needs_geometry_policy'
        else:
            stage='plan';candidate_plan.run(plan,out/'search/candidate',task,target,geometry_policy);result['stages']['plan']='materialized_verified'
            stage='requirements'
            request=dict(schema='bsa.module-request/1',project_id=out.name,scenario_id='terminal-design-iteration',capability='requirements.source-inventory',coordinate_frame=dict(id='requirements-no-geometry-claim',kind='source-world-si',length_unit='m',georeferenced=False),sources=dict(plan=dict(path=os.path.relpath(target,out),sha256=digest(target))))
            request_path=out/'requirements-request.json';request_path.write_text(json.dumps(request,indent=2),encoding='utf-8')
            inventory=modules.run(request_path,'bsa.source-requirements',out/'requirements',disabled='bsa.source-requirements' in options.get('disabled_module_providers',()))
            result['stages']['requirements']=inventory['execution']['status']
            if inventory['execution']['status']!='completed':result['status']='requirements_unavailable'
            else:
                stage='workflow';workflow.execute(target,out/'workflow',requirements_result=out/'requirements/result.json',**options);result['stages']['workflow']='executed'
                stage='diagnosis';diagnosis=workflow_status.diagnose(target,out/'workflow');(out/'diagnosis.json').write_text(json.dumps(diagnosis,indent=2),encoding='utf-8')
                result['stages']['diagnosis']='source_verified';result['actions']=diagnosis['actions'];result['engineering_actions']=diagnosis['engineering_actions']
                result['status']='needs_engineering_review' if diagnosis['execution_pass'] else 'execution_incomplete'
    except Exception as exc:
        result['status']='failed';result['stage_errors'][stage]=type(exc).__name__+': '+str(exc)
    result['original_inputs_unchanged']=all(Path(p).is_file() and digest(Path(p))==sha for p,sha in pins.items())
    if not result['original_inputs_unchanged']:result['status']='source_changed'
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    if manifest.is_file():result['target_provenance_sha256']=digest(manifest)
    (out/'iteration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def verify(folder):
    from .module_contract import read_json
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected iteration output required')
    result=read_json(folder/'iteration.json')
    fields={'schema','original_plan','original_run','performance_task','target_plan','search_policy','geometry_policy','inputs','module_selection','status','stages','original_requirements','original_unresolved_inputs','actions','engineering_actions','stage_errors','design_accepted','scope','original_inputs_unchanged','artifacts'}
    if 'target_provenance_sha256' in result:fields.add('target_provenance_sha256')
    if set(result)!=fields or result['schema']!='bsa.terminal-iteration/1' or result['design_accepted'] is not False or result['original_inputs_unchanged'] is not True or result['scope']!=SCOPE:raise ValueError('Unaccepted unchanged iteration evidence required')
    stage_order(result['stages'])
    plan=Path(result['original_plan']);original_run=Path(result['original_run']);policy=Path(result['search_policy']);geometry_policy=Path(result['geometry_policy']) if result['geometry_policy'] is not None else None;target=Path(result['target_plan'])
    if not all(allowed(p) for p in (plan,original_run,policy,target)) or geometry_policy is not None and not allowed(geometry_policy):raise ValueError('Selected iteration sources required')
    source,report,integrity=delivery.context(plan,original_run);task=result['performance_task']
    if not any(t['id']==task and t['kind']=='spatial_terminal_performance' for t in source['tasks']):raise ValueError('Original performance task differs')
    pins=input_pins(plan,original_run,policy,geometry_policy,report,original_run/task/'terminal-performance.json')
    if result['inputs']!=pins or any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Iteration input/source evidence changed')
    artifacts={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file() and p!=folder/'iteration.json'}
    if artifacts!=result['artifacts']:raise ValueError('Iteration artifact inventory changed')
    if not integrity['integrity_pass'] or result['original_requirements']!=source['requirements'] or result['original_unresolved_inputs']!=source.get('unresolved_inputs',[]):raise ValueError('Iteration replaced original assignment context')
    selection=result['module_selection']
    if host_selection(source['tasks'],selection['providers'],selection['disabled_providers'])!=selection:raise ValueError('Iteration host selection differs')
    expected='failed'
    if 'search' in result['stages']:
        studied=search.verify(folder/'search')
        search_link(studied,original_run/task/'terminal-performance.json',policy)
        if studied['proposal']['status']!=result['stages']['search']:raise ValueError('Iteration search stage differs')
        if studied['proposal']['status']=='no_feasible_candidate':expected='no_feasible_candidate'
        elif needs_geometry(source['tasks'],task) and geometry_policy is None:expected='needs_geometry_policy'
    if result['stages'].get('plan')=='materialized_verified':
        if expected in ('no_feasible_candidate','needs_geometry_policy'):raise ValueError('Blocked search/geometry stage released a plan')
        materialized=candidate_plan.verify(target)
        if materialized['original_plan']!=str(plan) or materialized['candidate']!=str(folder/'search/candidate') or materialized['task']!=task or materialized.get('geometry_policy')!=result['geometry_policy']:raise ValueError('Iteration plan replaced declared source/candidate/policy')
        if digest(target.with_suffix('.provenance.json'))!=result['target_provenance_sha256']:raise ValueError('Iteration target provenance changed')
    if 'requirements' in result['stages']:
        inventory=modules.verify_result(folder/'requirements/result.json')
        request_path=Path(inventory['request']['path']);request=read_json(request_path)
        if inventory['provider']['id']!='bsa.source-requirements' or inventory['capability']!='requirements.source-inventory' or (request_path.parent/request['sources']['plan']['path']).resolve()!=target:raise ValueError('Iteration inventory replaced selected provider/plan')
        if inventory['execution']['status']!=result['stages']['requirements']:raise ValueError('Iteration inventory stage differs')
        disabled='bsa.source-requirements' in selection['disabled_providers']
        actual=any(d['code']=='provider_disabled' for d in inventory['execution']['diagnostics'])
        if disabled!=actual:raise ValueError('Iteration inventory disable selection differs')
        if inventory['execution']['status']!='completed':expected='requirements_unavailable'
    if result['stages'].get('diagnosis')=='source_verified':
        if result['stages'].get('requirements')!='completed' or result['stages'].get('plan')!='materialized_verified' or result['stages'].get('workflow')!='executed':raise ValueError('Iteration released incomplete prerequisites')
        diagnosis=workflow_status.diagnose(target,folder/'workflow');new_report=read_json(folder/'workflow/workflow.json')
        if new_report['requirements_inventory']['result']!=str(folder/'requirements/result.json'):raise ValueError('Iteration workflow replaced its bound inventory')
        if new_report['module_selection']!=selection:raise ValueError('Iteration changed selected providers')
        if read_json(folder/'diagnosis.json')!=diagnosis or result['actions']!=diagnosis['actions'] or result['engineering_actions']!=diagnosis['engineering_actions']:raise ValueError('Iteration diagnosis/action queue differs')
        expected='needs_engineering_review' if diagnosis['execution_pass'] else 'execution_incomplete'
    elif result['actions'] or result['engineering_actions']:raise ValueError('Unverified diagnosis cannot publish action queues')
    if expected=='failed' and not result['stage_errors']:raise ValueError('Incomplete iteration lacks retained stage error')
    if result['stage_errors']:expected='failed'
    if result['status']!=expected:raise ValueError('Iteration status contradicts retained stages')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','original_run'):parser.add_argument(name)
    for name in ('task','policy','target','out'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--geometry-policy');parser.add_argument('--autocad');parser.add_argument('--moosas-upstream');parser.add_argument('--moosas-deps');parser.add_argument('--module-provider',action='append',default=[]);parser.add_argument('--disable-module-provider',action='append',default=[])
    a=parser.parse_args();options=dict(autocad=a.autocad,module_providers=parse_provider_options(a.module_provider),module_runtime=dict(upstream=a.moosas_upstream,deps=a.moosas_deps),disabled_module_providers=a.disable_module_provider)
    r=run(a.plan,a.original_run,a.task,a.policy,a.target,a.out,geometry_policy=a.geometry_policy,execute_options=options);print(json.dumps(dict(status=r['status'],stages=r['stages'],stage_errors=r['stage_errors'],design_accepted=False),indent=2));return 2

if __name__=='__main__':raise SystemExit(main())
