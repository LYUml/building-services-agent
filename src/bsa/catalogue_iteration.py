"""Replay a failed fan catalogue or pump curve revision through the full plan."""
import argparse
import copy
import json
import os
from pathlib import Path

from . import circular_fan_selection, pump, delivery, modules, workflow, workflow_status
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from .terminal_iteration import OPTIONS

SCOPE='Explicit host fan catalogue or pump curve revision with unchanged original requirements and targets; not autonomous product approval or full engineering acceptance'


def revision_field(task):
    fields={'circular_fan_selection':'catalogue','pump_operating_point':'curve'}
    if task['kind'] not in fields:raise ValueError('Supported fan selection or pump operating task required')
    return fields[task['kind']]


def selection_context(task,source,plan,original,replacement):
    if task['kind']=='circular_fan_selection':
        pressure=original/task['depends_on']
        _,_,inputs,_,_,_=circular_fan_selection.context(pressure,replacement)
        return pressure,inputs
    revision_field(task)
    parent=task.get('depends_on')
    known={t['id']:t for t in source['tasks']}
    network=original/parent/workflow.NETWORK_ARTIFACTS[known[parent]['kind']] if parent else workflow.local_path(plan.parent,task['project'])
    pump.prepare(read_json(network),read_json(replacement))
    return network,{str(p):digest(p) for p in (network,replacement)}


def selection_run(task,context,replacement,out):
    return (pump.run if task['kind']=='pump_operating_point' else circular_fan_selection.run)(context,replacement,out)


def selection_report(task):
    return 'pump.json' if task['kind']=='pump_operating_point' else 'fan-selection.json'


def selection_modules(task):
    if task['kind']=='pump_operating_point':
        from . import network,pump_electrical
        return (pump,network,pump_electrical)
    return (circular_fan_selection,)


def revised_plan(source,task,catalogue,target):
    if not catalogue.is_relative_to(target.parent):raise ValueError('Revised catalogue must be inside the plan input directory')
    result=copy.deepcopy(source)
    selected=next(t for t in result['tasks'] if t['id']==task)
    selected[revision_field(selected)]=os.path.relpath(catalogue,target.parent)
    return result


def baseline_signature(result):
    if 'candidates' not in result:
        return {key:result.get(key) for key in ('status','reason','calculated_checks_pass','checks','operating_point','flow_bracket_m3_s','selected_rerun_pass')}
    return [(row['id'],row['preference'],{key:row.get(key) for key in
             ('status','calculated_checks_pass','checks','operating_point')})
            for row in result['candidates']]


def run(plan,original_run,task,catalogue,target,out,*,execute_options=None):
    plan,original_run,catalogue,target,out=[Path(p).resolve() for p in (plan,original_run,catalogue,target,out)]
    if not all(allowed(p) for p in (plan,original_run,catalogue,target,out)):
        raise ValueError('Selected project workspace required')
    if target.parent!=plan.parent or target.suffix!='.json' or target.exists() or out.exists():
        raise ValueError('Fresh output and same-directory new plan required')
    if not catalogue.is_relative_to(plan.parent):raise ValueError('Revised catalogue must be inside the plan input directory')
    if any(out==p or out in p.parents for p in (plan,original_run,catalogue,target)) or out.is_relative_to(original_run) or target.is_relative_to(original_run):
        raise ValueError('Recovery outputs must preserve original sources and run')
    options={} if execute_options is None else dict(execute_options)
    if set(options)-OPTIONS:raise ValueError('Supported host runtime options required')
    source,report,integrity=delivery.context(plan,original_run)
    if not integrity['integrity_pass']:raise ValueError('Original workflow evidence is stale')
    diagnosis=workflow_status.diagnose(plan,original_run)
    tasks={t['id']:t for t in source['tasks']}
    if task not in tasks or tasks[task]['kind'] not in ('circular_fan_selection','pump_operating_point') or report['tasks'][task]['status']!='fail' or task not in diagnosis['recovery_schedule']['ready_tasks']:
        raise ValueError('Ready failed fan selection or pump operating task required')
    selected=tasks[task]
    old_catalogue=workflow.local_path(plan.parent,selected[revision_field(selected)])
    if digest(old_catalogue)==digest(catalogue):raise ValueError('Explicit revised catalogue must differ from failed source')
    old=read_json(original_run/task/selection_report(selected))
    if old.get('selected') is not None or old.get('calculated_checks_pass') is not False:
        raise ValueError('Failed no-selection baseline required')
    # Validate the replacement against the exact inherited pressure/native source.
    pressure,new_inputs=selection_context(selected,source,plan,original_run,catalogue)
    pins={**report['inputs'],**new_inputs,str(plan):digest(plan),
          str(original_run/'workflow.json'):digest(original_run/'workflow.json')}
    pins.update({str(original_run/name):sha for name,sha in report['artifact_hashes'].items()})
    for module in (delivery,modules,workflow,workflow_status,*selection_modules(selected)):
        pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    out.mkdir(parents=True)
    result=dict(schema='bsa.catalogue-iteration/1',plan=str(plan),original_run=str(original_run),
        task=task,catalogue=str(catalogue),target_plan=str(target),inputs=pins,
        original_requirements=source['requirements'],original_unresolved_inputs=source.get('unresolved_inputs',[]),
        scope=SCOPE,design_accepted=False,status='failed',stages={},stage_errors={})
    stage='baseline'
    try:
        baseline=selection_run(selected,pressure,old_catalogue,out/'baseline-recheck')
        if baseline.get('selected') is not None or baseline['calculated_checks_pass'] is not False or baseline_signature(old)!=baseline_signature(baseline):
            raise ValueError('Original failed selection differs from fresh source replay')
        result['stages']['baseline']='failure_reproduced'
        stage='plan'
        revised=revised_plan(source,task,catalogue,target)
        target.write_text(json.dumps(revised,indent=2),encoding='utf-8')
        workflow.validate_plan(target)
        result['target_plan_sha256']=digest(target)
        result['stages']['plan']='materialized_verified'
        stage='requirements'
        request=dict(schema='bsa.module-request/1',project_id=out.name,scenario_id='catalogue-recovery',
            capability='requirements.source-inventory',coordinate_frame=dict(id='requirements-no-geometry-claim',kind='source-world-si',length_unit='m',georeferenced=False),
            sources=dict(plan=dict(path=os.path.relpath(target,out),sha256=digest(target))))
        request_path=out/'requirements-request.json';request_path.write_text(json.dumps(request,indent=2),encoding='utf-8')
        inventory=modules.run(request_path,'bsa.source-requirements',out/'requirements',disabled='bsa.source-requirements' in options.get('disabled_module_providers',()))
        result['stages']['requirements']=inventory['execution']['status']
        if inventory['execution']['status']!='completed':result['status']='requirements_unavailable'
        else:
            stage='workflow';workflow.execute(target,out/'workflow',requirements_result=out/'requirements/result.json',**options)
            result['stages']['workflow']='executed'
            stage='diagnosis';fresh=workflow_status.diagnose(target,out/'workflow')
            (out/'diagnosis.json').write_text(json.dumps(fresh,indent=2),encoding='utf-8')
            result['stages']['diagnosis']='source_verified'
            result['status']='needs_engineering_review' if fresh['execution_pass'] else 'execution_incomplete'
    except Exception as exc:result['stage_errors'][stage]=type(exc).__name__+': '+str(exc)
    result['original_inputs_unchanged']=all(Path(p).is_file() and digest(Path(p))==sha for p,sha in pins.items())
    if not result['original_inputs_unchanged']:result['status']='source_changed'
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'iteration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan');parser.add_argument('original_run')
    for name in ('task','target','out'):parser.add_argument('--'+name,required=True)
    replacement=parser.add_mutually_exclusive_group(required=True)
    replacement.add_argument('--catalogue');replacement.add_argument('--curve',dest='catalogue')
    args=parser.parse_args();result=run(args.plan,args.original_run,args.task,args.catalogue,args.target,args.out)
    print(json.dumps(result,indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
