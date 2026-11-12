"""Bind explicit host interpretation to existing engineering adapters, preserving sources."""
import argparse
import copy
import json
import os
from pathlib import Path

from . import modules,workflow,workflow_status
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from .terminal_iteration import OPTIONS

GENERIC='Source meaning, design inputs and acceptance criteria have not been interpreted.'
SCOPE='Host-reviewed source-to-adapter handoff; source coverage is checked, semantic completeness and full engineering acceptance are not established'


def template(plan,output):
    """Create the exact review contract, with unresolved decisions deliberately empty."""
    plan,output=[Path(p).resolve() for p in (plan,output)]
    if not all(allowed(p) for p in (plan,output)) or output.parent!=plan.parent or output.exists():
        raise ValueError('Fresh sibling engineering interpretation required')
    source,inputs=workflow.validate_plan(plan)
    if any(t['kind']!='manual' for t in source['tasks']):
        raise ValueError('Manual interpretation plan required; existing engineering tasks cannot be replaced')
    pins={p:digest(p) for p in (plan,*inputs)}
    generic={i['id'] for i in source.get('unresolved_inputs',[]) if i['kind']=='missing' and i['id'].startswith('interpretation-') and i['description']==GENERIC}
    record=dict(schema='bsa.engineering-handoff/1',source_plan_sha256=pins[plan],tasks=[],
        requirement_bindings={r['id']:dict(tasks=[],acceptance='') for r in source['requirements']},
        interpretation_notes={key:'' for key in sorted(generic)},extra_unresolved_inputs=[])
    if any(digest(p)!=sha for p,sha in pins.items()):raise ValueError('Source changed during interpretation preparation')
    with output.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2,ensure_ascii=False)
    return dict(status='needs_interpretation',review=str(output),source_plan_sha256=pins[plan],
        original_requirements=len(source['requirements']),retained_input_gaps=len(source.get('unresolved_inputs',[])),
        executable=False,design_accepted=False)


def materialize(source,record):
    if any(t['kind']!='manual' for t in source['tasks']):raise ValueError('Manual interpretation plan required; existing engineering tasks cannot be replaced')
    fields={'schema','source_plan_sha256','tasks','requirement_bindings','interpretation_notes','extra_unresolved_inputs'}
    if set(record)!=fields or record['schema']!='bsa.engineering-handoff/1':raise ValueError('Exact engineering handoff schema required')
    bindings=record['requirement_bindings'];requirements=source['requirements']
    if not isinstance(bindings,dict) or set(bindings)!={r['id'] for r in requirements}:raise ValueError('Every original requirement must have an explicit binding')
    tasks=copy.deepcopy(record['tasks'])
    if not isinstance(tasks,list) or not tasks or any(not isinstance(t,dict) or not isinstance(t.get('id'),str) for t in tasks):raise ValueError('Explicit adapter tasks required')
    known={t['id'] for t in tasks}
    if len(known)!=len(tasks):raise ValueError('Unique adapter tasks required')
    old_targets={t['id']:set() for t in source['tasks']};used=set();mapped=[]
    for original in requirements:
        binding=bindings[original['id']]
        if not isinstance(binding,dict) or set(binding)!={'tasks','acceptance'}:raise ValueError('Task mapping and explicit acceptance required')
        targets=binding['tasks'];acceptance=binding['acceptance']
        if not isinstance(targets,list) or not targets or any(not isinstance(t,str) or t not in known for t in targets) or len(set(targets))!=len(targets) or not isinstance(acceptance,str) or not acceptance.strip():raise ValueError('Known unique task bindings and acceptance required')
        old_targets[original['task']].update(targets);used.update(targets)
        for index,target in enumerate(targets,1):
            mapped.append(dict(original,id=original['id']+'-bound-'+str(index),task=target,
                original_requirement_id=original['id'],original_acceptance=original['acceptance'],acceptance=acceptance))
    if used!=known:raise ValueError('Every adapter task needs original requirement coverage')
    for old in source['tasks']:
        parents=list(old.get('requires_pass',[]))+[old[k] for k in ('depends_on','ifc_from','junction_from','connector_from') if old.get(k)]
        inherited={p for parent in parents for p in old_targets[parent]}
        if inherited & old_targets[old['id']]:raise ValueError('Cannot collapse original dependent obligations into one task')
        for task in tasks:
            if task['id'] in old_targets[old['id']] and inherited:
                task['requires_pass']=list(dict.fromkeys(task.get('requires_pass',[])+sorted(inherited)))
    issues=source.get('unresolved_inputs',[])
    generic={i['id'] for i in issues if i['kind']=='missing' and i['id'].startswith('interpretation-') and i['description']==GENERIC}
    notes=record['interpretation_notes']
    if not isinstance(notes,dict) or set(notes)!=generic or any(not isinstance(n,str) or not n.strip() for n in notes.values()):raise ValueError('Explicit interpretation notes required for every generic interpretation gap')
    retained=[]
    for issue in issues:
        if issue['id'] in generic:continue
        row=copy.deepcopy(issue);row['blocks_tasks']=sorted({t for old in issue['blocks_tasks'] for t in old_targets[old]});retained.append(row)
    if not isinstance(record['extra_unresolved_inputs'],list):raise ValueError('Additional source-linked gaps must be a list')
    result=copy.deepcopy(source);result.update(tasks=tasks,requirements=mapped,
        unresolved_inputs=retained+copy.deepcopy(record['extra_unresolved_inputs']))
    return result


def apply(plan,record,output):
    plan,record,output=[Path(p).resolve() for p in (plan,record,output)]
    if not all(allowed(p) for p in (plan,record,output)) or record.parent!=plan.parent or output.parent!=plan.parent or output.exists():raise ValueError('Fresh sibling plan and project-local host review required')
    source,inputs=workflow.validate_plan(plan);pins={str(p):digest(p) for p in (plan,record,*inputs)}
    review=read_json(record)
    if review.get('source_plan_sha256')!=digest(plan):raise ValueError('Host interpretation references a different source plan')
    result=materialize(source,review)
    result['planning_records']=list(dict.fromkeys(source.get('planning_records',[])+[plan.name,record.name]))
    candidate=output.with_name(output.name+'.candidate')
    if candidate.exists():raise ValueError('Fresh handoff candidate required')
    try:
        with candidate.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,ensure_ascii=False)
        _,bound_files=workflow.validate_plan(candidate)
        bound_inputs={str(p):digest(p) for p in bound_files}
        if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Handoff sources changed during validation')
        if any(digest(Path(p))!=sha for p,sha in bound_inputs.items()):raise ValueError('Bound engineering inputs changed during handoff')
        with output.open('xb') as stream:stream.write(candidate.read_bytes())
    finally:
        if candidate.exists():candidate.unlink()
    return dict(source_plan=str(plan),source_plan_sha256=digest(plan),review=str(record),review_sha256=digest(record),
        plan=str(output),plan_sha256=digest(output),original_requirements=len(source['requirements']),
        bound_requirements=len(result['requirements']),retained_input_gaps=len(result['unresolved_inputs']),bound_inputs=bound_inputs,
        scope=SCOPE,design_accepted=False)


def run(plan,record,output,out,*,execute_options=None):
    plan,record,output,out=[Path(p).resolve() for p in (plan,record,output,out)]
    options={} if execute_options is None else dict(execute_options)
    if set(options)-OPTIONS:raise ValueError('Explicit supported host runtime options required')
    if not allowed(out) or out.exists() or any(out==p or out in p.parents for p in (plan,record,output)):
        raise ValueError('Fresh run separate from source plans and review required')
    handoff=apply(plan,record,output);out.mkdir(parents=True)
    pins={**handoff['bound_inputs'],str(Path(__file__).resolve()):digest(Path(__file__)),str(output):digest(output),str(plan):digest(plan),str(record):digest(record)}
    result=dict(handoff=handoff,inputs=pins,stages={'plan':'materialized_verified'},stage_errors={},status='failed',design_accepted=False,scope=SCOPE)
    stage='requirements'
    try:
        if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Bound engineering inputs changed before execution')
        request=dict(schema='bsa.module-request/1',project_id=out.name,scenario_id='engineering-handoff',capability='requirements.source-inventory',
            coordinate_frame=dict(id='requirements-no-geometry-claim',kind='source-world-si',length_unit='m',georeferenced=False),sources=dict(plan=dict(path=os.path.relpath(output,out),sha256=digest(output))))
        request_path=out/'requirements-request.json';request_path.write_text(json.dumps(request,indent=2),encoding='utf-8')
        inventory=modules.run(request_path,'bsa.source-requirements',out/'requirements',disabled='bsa.source-requirements' in options.get('disabled_module_providers',()))
        result['stages']['requirements']=inventory['execution']['status']
        if inventory['execution']['status']!='completed':result['status']='requirements_unavailable'
        else:
            stage='workflow';workflow.execute(output,out/'workflow',requirements_result=out/'requirements/result.json',**options);result['stages']['workflow']='executed'
            stage='diagnosis';diagnosis=workflow_status.diagnose(output,out/'workflow')
            (out/'diagnosis.json').write_text(json.dumps(diagnosis,indent=2),encoding='utf-8');result['stages']['diagnosis']='source_verified'
            result['status']='needs_engineering_review' if diagnosis['execution_pass'] else 'execution_incomplete'
    except Exception as exc:result['stage_errors'][stage]=type(exc).__name__+': '+str(exc)
    result['inputs_unchanged']=all(Path(p).is_file() and digest(Path(p))==sha for p,sha in pins.items())
    if not result['inputs_unchanged']:result['status']='source_changed'
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'handoff.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan');parser.add_argument('review');parser.add_argument('--target',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();result=run(args.plan,args.review,args.target,args.out)
    print(json.dumps({k:result[k] for k in ('status','stages','stage_errors','design_accepted')},indent=2));return 2


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected handoff workspace required')
    result=read_json(out/'handoff.json')
    if result.get('scope')!=SCOPE or result.get('design_accepted') is not False or result.get('inputs_unchanged') is not True or not result.get('inputs'):
        raise ValueError('Unaccepted unchanged engineering handoff required')
    if any(not allowed(Path(p)) or not Path(p).is_file() or digest(Path(p))!=sha for p,sha in result['inputs'].items()):raise ValueError('Handoff source or method changed')
    artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file() and p!=out/'handoff.json'}
    if artifacts!=result.get('artifacts'):raise ValueError('Handoff artifacts changed')
    handoff=result['handoff'];plan,record,target=[Path(handoff[k]).resolve() for k in ('source_plan','review','plan')]
    if not all(allowed(p) for p in (plan,record,target)) or not(plan.parent==record.parent==target.parent):raise ValueError('Handoff plan/review source identity changed')
    required={str(p):digest(p) for p in (plan,record,target,Path(__file__).resolve())}
    if any(result['inputs'].get(p)!=sha for p,sha in required.items()):raise ValueError('Handoff omitted source or method pins')
    source,_=workflow.validate_plan(plan);review=read_json(record)
    if review.get('source_plan_sha256')!=digest(plan):raise ValueError('Host review source plan changed')
    expected=materialize(source,review)
    expected['planning_records']=list(dict.fromkeys(source.get('planning_records',[])+[plan.name,record.name]))
    if read_json(target)!=expected:raise ValueError('Bound plan differs from source-preserving interpretation')
    _,bound_files=workflow.validate_plan(target);bound_inputs={str(p):digest(p) for p in bound_files}
    if any(result['inputs'].get(p)!=sha for p,sha in bound_inputs.items()):raise ValueError('Handoff omitted bound engineering input pins')
    expected_handoff=dict(source_plan=str(plan),source_plan_sha256=digest(plan),review=str(record),review_sha256=digest(record),plan=str(target),plan_sha256=digest(target),
        original_requirements=len(source['requirements']),bound_requirements=len(expected['requirements']),retained_input_gaps=len(expected['unresolved_inputs']),bound_inputs=bound_inputs,scope=SCOPE,design_accepted=False)
    if handoff!=expected_handoff:raise ValueError('Handoff receipt differs from original requirements or gaps')
    if result.get('stages')!=dict(plan='materialized_verified',requirements='completed',workflow='executed',diagnosis='source_verified') or result.get('stage_errors'):raise ValueError('Handoff stages incomplete')
    inventory=modules.verify_result(out/'requirements/result.json')
    if inventory['execution']['status']!='completed':raise ValueError('Incomplete requirements inventory')
    fresh=workflow_status.diagnose(target,out/'workflow');report=read_json(out/'workflow/workflow.json')
    if report['requirements_inventory']['result']!=str(out/'requirements/result.json'):raise ValueError('Handoff replaced requirements inventory')
    if read_json(out/'diagnosis.json')!=fresh:raise ValueError('Handoff diagnosis changed')
    status='needs_engineering_review' if fresh['execution_pass'] else 'execution_incomplete'
    if result.get('status')!=status:raise ValueError('Handoff status differs from actual execution')
    return dict(integrity_pass=True,original_requirement_ids=[r['id'] for r in source['requirements']],
        task_statuses={name:row['status'] for name,row in report['tasks'].items()},retained_input_gaps=expected['unresolved_inputs'],
        recovery_schedule=fresh['recovery_schedule'],design_accepted=False,semantic_completeness='not_established')


if __name__=='__main__':raise SystemExit(main())
