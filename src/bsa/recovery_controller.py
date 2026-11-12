"""Bounded diagnosed pump recovery using declared source catalogues and full replays."""
import json
from pathlib import Path
from . import delivery,workflow,workflow_status,pump_catalogue_iteration as pump
from .cli import digest
from .module_contract import read_json
from .terminal_iteration import OPTIONS
from .workspace import allowed


def policy(plan,path):
    data=read_json(path)
    if set(data)!={'schema','max_steps','actions'} or data['schema']!='bsa.recovery-policy/1' or type(data['max_steps']) is not int or not 1<=data['max_steps']<=20:
        raise ValueError('Bounded recovery policy required')
    if not isinstance(data['actions'],list) or len(data['actions'])>20:raise ValueError('At most twenty declared recovery actions required')
    tasks={t['id']:t for t in read_json(plan)['tasks']};seen=set()
    for row in data['actions']:
        if not isinstance(row,dict) or set(row)-{'task','catalogue','electrical_task'} or not {'task','catalogue'}<=set(row):raise ValueError('Explicit task and catalogue action required')
        task=row['task']
        if task in seen or tasks.get(task,{}).get('kind')!='pump_operating_point':raise ValueError('Unique existing pump task required')
        seen.add(task);catalogue=workflow.local_path(Path(plan).parent,row['catalogue']);pump.candidates(read_json(catalogue))
        if row.get('electrical_task') is not None:
            linked=tasks.get(row['electrical_task'],{})
            if linked.get('kind')!='pump_electrical' or linked.get('depends_on')!=task:raise ValueError('Original downstream electrical consumer required')
    return data


def decision(diagnosis,data,attempted):
    ready=set(diagnosis['recovery_schedule']['ready_tasks'])
    states={t['id']:t for t in diagnosis['tasks']}
    return next((row for row in data['actions'] if row['task'] in ready and states[row['task']]['status']=='fail' and not states[row['task']]['input_blockers'] and row['task'] not in attempted),None)


def final_status(diagnosis,data,attempted,steps):
    if diagnosis['execution_pass']:return 'execution_pass_review_pending'
    if steps and not steps[-1]['selected']:return steps[-1]['status']
    if len(steps)>=data['max_steps'] and decision(diagnosis,data,attempted):return 'step_limit'
    return 'needs_action_or_review'


def run(plan,original,policy_path,out,*,execute_options=None):
    plan,original,policy_path,out=[Path(p).resolve() for p in (plan,original,policy_path,out)]
    if not all(allowed(p) for p in (plan,original,policy_path,out)) or not out.is_relative_to(plan.parent) or out.is_relative_to(original) or any(out==p or out in p.parents for p in (plan,original,policy_path)) or out.exists():raise ValueError('Fresh project-local controller output separate from sources/run required')
    if set(execute_options or {})-OPTIONS:raise ValueError('Fixed supported host options required')
    data=policy(plan,policy_path);diagnosis=workflow_status.diagnose(plan,original)
    source,report,integrity=delivery.context(plan,original)
    if not integrity['integrity_pass']:raise ValueError('Fresh source-bound workflow required')
    pins={str(plan):digest(plan),str(policy_path):digest(policy_path),str(original/'workflow.json'):digest(original/'workflow.json'),str(Path(__file__).resolve()):digest(Path(__file__))}
    for row in data['actions']:
        path=workflow.local_path(plan.parent,row['catalogue']);pins[str(path)]=digest(path)
    out.mkdir(parents=True);current_plan,current_run=plan,original;steps=[];attempted=set()
    while len(steps)<data['max_steps']:
        action=decision(diagnosis,data,attempted)
        if action is None:break
        task=action['task'];attempted.add(task);number=len(steps)+1
        target=plan.parent/(out.name+'-step-'+str(number)+'-plan.json');folder=out/('step-'+str(number))
        if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Controller sources changed')
        result=pump.run(current_plan,current_run,task,workflow.local_path(plan.parent,action['catalogue']),target,folder,electrical_task=action.get('electrical_task'),execute_options=execute_options)
        checked=pump.verify(folder);selected=checked['selected']
        steps.append(dict(task=task,input_plan=str(current_plan),input_run=str(current_run),output=str(folder),target=str(target),selected=selected,status=result['status']))
        if not selected:break
        current_plan,current_run=target,folder/'replay/workflow'
        diagnosis=workflow_status.diagnose(current_plan,current_run)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Controller sources changed')
    result=dict(schema='bsa.recovery-controller/1',plan=str(plan),original_run=str(original),policy=str(policy_path),inputs=pins,steps=steps,final_plan=str(current_plan),final_run=str(current_run),diagnosis=diagnosis,status=final_status(diagnosis,data,attempted,steps),design_accepted=False)
    (out/'recovery.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected controller output required')
    result=read_json(out/'recovery.json')
    if set(result)!={'schema','plan','original_run','policy','inputs','steps','final_plan','final_run','diagnosis','status','design_accepted'} or result.get('schema')!='bsa.recovery-controller/1' or result.get('design_accepted') is not False:raise ValueError('Unaccepted recovery record required')
    plan,original,path=[Path(result[k]).resolve() for k in ('plan','original_run','policy')]
    if not all(allowed(p) for p in (plan,original,path)) or not out.is_relative_to(plan.parent) or out.is_relative_to(original) or any(out==p or out in p.parents for p in (plan,original,path)):raise ValueError('Controller source/output boundary changed')
    data=policy(plan,path)
    expected={str(plan):digest(plan),str(path):digest(path),str(original/'workflow.json'):digest(original/'workflow.json'),str(Path(__file__).resolve()):digest(Path(__file__))}
    for row in data['actions']:
        p=workflow.local_path(plan.parent,row['catalogue']);expected[str(p)]=digest(p)
    if result.get('inputs')!=expected:raise ValueError('Controller source pins changed')
    diagnosis=workflow_status.diagnose(plan,original);current_plan,current_run=plan,original;attempted=set()
    if len(result['steps'])>data['max_steps']:raise ValueError('Controller exceeded declared step limit')
    for number,row in enumerate(result['steps'],1):
        action=decision(diagnosis,data,attempted)
        if action is None or row['task']!=action['task']:raise ValueError('Controller action differs from fresh ready diagnosis')
        folder=out/('step-'+str(number));target=plan.parent/(out.name+'-step-'+str(number)+'-plan.json')
        checked=pump.verify(folder);child=read_json(folder/'selection.json')
        expected_row=dict(task=action['task'],input_plan=str(current_plan),input_run=str(current_run),output=str(folder),target=str(target),selected=checked['selected'],status=child['status'])
        if row!=expected_row or child['plan']!=str(current_plan) or child['original_run']!=str(current_run) or child['task']!=action['task'] or child['target_plan']!=str(target) or child['catalogue']!=str(workflow.local_path(plan.parent,action['catalogue'])) or child['electrical_task']!=action.get('electrical_task'):raise ValueError('Controller replaced a declared recovery action')
        attempted.add(action['task'])
        if not checked['selected']:
            if number!=len(result['steps']):raise ValueError('Controller continued after inconclusive screening')
            break
        current_plan,current_run=target,folder/'replay/workflow';diagnosis=workflow_status.diagnose(current_plan,current_run)
    stopped=bool(result['steps'] and not result['steps'][-1]['selected'])
    if not stopped and len(result['steps'])<data['max_steps'] and decision(diagnosis,data,attempted):raise ValueError('Controller omitted a ready declared recovery')
    if result.get('final_plan')!=str(current_plan) or result.get('final_run')!=str(current_run) or result.get('diagnosis')!=diagnosis or result.get('status')!=final_status(diagnosis,data,attempted,result['steps']):raise ValueError('Controller final diagnosis differs')
    return dict(integrity_pass=True,steps=len(result['steps']),status=result['status'],execution_pass=diagnosis['execution_pass'],design_accepted=False)
