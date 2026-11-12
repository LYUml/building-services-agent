"""Screen supplied pump curves, then replay the full original coupled plan."""
import argparse
import json
from pathlib import Path

from . import catalogue_iteration as iteration,catalogue_iteration_verify,delivery,pump
from . import rectangular_fan_selection as preference,pump_electrical,engine
from .cli import digest
from .engine import ProjectError
from .module_contract import read_json
from .workspace import allowed

SCOPE='Bounded supplied pump curves ranked on original hydraulic targets and optional explicit downstream steady electrical checks, then full-plan replay; not manufacturer discovery or complete equipment/engineering approval'
FIELDS=('status','calculated_checks_pass','checks','operating_point')


def candidates(data):
    if not isinstance(data,dict) or set(data)!={'objective','source','candidates'}:raise ValueError('Exact sourced pump catalogue required')
    return preference.candidates(data,curve_validator=pump.validate_curve)


def context(plan,original,task,catalogue,electrical_task=None):
    if not all(allowed(p) for p in (plan,original,catalogue)):raise ValueError('Selected project workspace required')
    source,report,integrity=delivery.context(plan,original)
    if not integrity['integrity_pass']:raise ValueError('Original workflow is stale')
    tasks={t['id']:t for t in source['tasks']}
    diagnosis=iteration.workflow_status.diagnose(plan,original)
    if task not in tasks or tasks[task]['kind']!='pump_operating_point' or report['tasks'][task]['status']!='fail' or task not in diagnosis['recovery_schedule']['ready_tasks']:
        raise ValueError('Ready failed pump operating task required')
    selected=tasks[task];curve=iteration.workflow.local_path(plan.parent,selected['curve'])
    network,_=iteration.selection_context(selected,source,plan,original,curve)
    options=candidates(read_json(catalogue))
    electrical=None
    if electrical_task is not None:
        linked=tasks.get(electrical_task,{})
        if linked.get('kind')!='pump_electrical' or linked.get('depends_on')!=task:raise ValueError('Explicit original downstream pump-electrical task required')
        project=iteration.workflow.local_path(plan.parent,linked['project']);link=iteration.workflow.local_path(plan.parent,linked['link'])
        electrical=(engine.validate(read_json(project)),pump_electrical.validate_link(read_json(link)))
        if not any(d['id']==electrical[1]['electrical_device_id'] for d in electrical[0]['devices']):raise ValueError('Unknown original electrical device')
    fresh,operating=pump.solve(read_json(network),read_json(curve))
    fresh['selected_rerun_pass']=bool(operating is not None and pump.calculate(operating)['calculated_checks_pass'])
    old=read_json(original/task/'pump.json')
    if fresh['calculated_checks_pass'] is not False or iteration.baseline_signature(fresh)!=iteration.baseline_signature(old):raise ValueError('Original pump failure cannot be reconstructed')
    pins={**report['inputs'],str(plan):digest(plan),str(catalogue):digest(catalogue),str(original/'workflow.json'):digest(original/'workflow.json')}
    pins.update({str(original/name):sha for name,sha in report['artifact_hashes'].items()})
    for module in (iteration,catalogue_iteration_verify,delivery,preference,engine,*iteration.selection_modules(selected)):
        pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return source,network,options,pins,electrical


def eligibility(summary,electrical):
    if electrical is None:return summary
    result=dict(summary,numerical_checks_pass=summary['calculated_checks_pass'])
    if not summary['calculated_checks_pass']:
        result['electrical']=dict(status='not_evaluated',reason='Original hydraulic checks did not pass')
        return result
    point=summary['operating_point']
    if point['estimated_electrical_kw'] is None:
        result.update(calculated_checks_pass=False,eligibility_pending=True,
            electrical=dict(status='pending',reason='Combined wire-to-water efficiency is missing; operating electrical input is unknown'))
        return result
    baseline,link=electrical
    projected=pump_electrical.operating_project(baseline,link,point,'Source-pinned candidate curve conditional screening')
    checks=engine.calculate(projected)
    result.update(calculated_checks_pass=checks['calculated_checks_pass'],electrical=dict(status='pass' if checks['calculated_checks_pass'] else 'fail',
        operating_input_kw=point['estimated_electrical_kw'],power_factor=link['operating_power_factor'],circuits=checks['circuits'],
        scope='Original steady-load current,ampacity and branch voltage-drop checks only; no motor starting,protection or full statutory acceptance'))
    return result


def numerical(network,curve,electrical=None):
    try:
        result,_=pump.solve(network,curve)
        summary={k:result.get(k) for k in FIELDS}
    except ProjectError as exc:summary=dict(status='unsupported',calculated_checks_pass=False,reason=str(exc))
    return eligibility(summary,electrical)


def run(plan,original,task,catalogue,target,out,*,execute_options=None,electrical_task=None):
    plan,original,catalogue,target,out=[Path(p).resolve() for p in (plan,original,catalogue,target,out)]
    if out.exists() or target.exists() or not out.is_relative_to(plan.parent) or target.parent!=plan.parent or target.is_relative_to(out) or any(out==p or out in p.parents for p in (plan,original,catalogue)) or out.is_relative_to(original):
        raise ValueError('Fresh project-local screening folder and separate sibling target plan required')
    if set(execute_options or {})-iteration.OPTIONS:raise ValueError('Supported explicit host runtime options required')
    source,network,options,pins,electrical=context(plan,original,task,catalogue,electrical_task)
    out.mkdir(parents=True)
    def unchanged():
        if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Pump selection source or method changed')
    def evaluate(row,name):
        unchanged();folder=out/name;folder.mkdir()
        curve=folder/'curve.json';curve.write_text(json.dumps(row['curve'],indent=2),encoding='utf-8')
        try:
            result=pump.run(network,curve,folder/'operating')
            summary={k:result.get(k) for k in FIELDS}
        except ProjectError as exc:summary=dict(status='unsupported',calculated_checks_pass=False,reason=str(exc))
        unchanged();return eligibility(summary,electrical)
    screen=preference.screen(options,evaluate)
    result=dict(schema='bsa.pump-catalogue-iteration/1',scope=SCOPE,plan=str(plan),original_run=str(original),task=task,
        catalogue=str(catalogue),electrical_task=electrical_task,target_plan=str(target),inputs=pins,screening=screen,status='needs_candidate_evidence' if screen['unresolved_preference'] else 'no_feasible_candidate',
        original_requirements=source['requirements'],original_unresolved_inputs=source.get('unresolved_inputs',[]),design_accepted=False)
    if screen['selected']:
        replay=iteration.run(plan,original,task,out/'selected/curve.json',target,out/'replay',execute_options=execute_options)
        result['status']=replay['status'];result['target_plan_sha256']=digest(target) if target.is_file() else None
    unchanged()
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'selection.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected screening workspace required')
    result=read_json(out/'selection.json')
    if result.get('schema')!='bsa.pump-catalogue-iteration/1' or result.get('scope')!=SCOPE or result.get('design_accepted') is not False:raise ValueError('Unaccepted pump screening receipt required')
    plan,original,catalogue,target=[Path(result[k]).resolve() for k in ('plan','original_run','catalogue','target_plan')]
    source,network,options,pins,electrical=context(plan,original,result['task'],catalogue,result.get('electrical_task'))
    if result.get('inputs')!=pins or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Pump screening source pins differ')
    if result.get('artifacts')!={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file() and p!=out/'selection.json'}:raise ValueError('Pump screening artifacts changed')
    expected=preference.screen(options,lambda row,name:numerical(read_json(network),row['curve'],electrical))
    if result.get('screening')!=expected:raise ValueError('Pump preference or candidates differ from source replay')
    if result.get('original_requirements')!=source['requirements'] or result.get('original_unresolved_inputs')!=source.get('unresolved_inputs',[]):raise ValueError('Pump screening removed source obligations or gaps')
    for index,row in enumerate(options):
        folder=out/f'candidate-{index:03d}'
        if read_json(folder/'curve.json')!=row['curve']:raise ValueError('Saved pump candidate curve differs')
        record=expected['candidates'][index]
        if record['status']!='unsupported':
            saved=read_json(folder/'operating/pump.json')
            hydraulic=numerical(read_json(network),row['curve'])
            if any(saved.get(k)!=hydraulic.get(k) for k in FIELDS):raise ValueError('Saved pump candidate result differs')
    if expected['selected']:
        selected=next(row for row in options if row['id']==expected['selected']['id'])
        if read_json(out/'selected/curve.json')!=selected['curve']:raise ValueError('Selected pump curve differs')
        checked=catalogue_iteration_verify.verify(out/'replay')
        replay=read_json(out/'replay/iteration.json')
        if replay['catalogue']!=str(out/'selected/curve.json') or replay['plan']!=str(plan) or replay['original_run']!=str(original) or replay['task']!=result['task'] or replay['target_plan']!=str(target) or result.get('target_plan_sha256')!=digest(target) or result.get('status')!=replay['status']:raise ValueError('Pump screening replaced full-plan replay')
    else:
        status='needs_candidate_evidence' if expected['unresolved_preference'] else 'no_feasible_candidate'
        if result.get('status')!=status or target.exists() or (out/'replay').exists():raise ValueError('Unselected pump created a downstream plan or replay')
    return dict(integrity_pass=True,candidates=len(options),selected=expected['selected']['id'] if expected['selected'] else None,
        requirements_preserved=True,full_plan_executed=bool(expected['selected']),design_accepted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('plan');p.add_argument('original_run')
    for key in ('task','catalogue','target','out'):p.add_argument('--'+key,required=True)
    p.add_argument('--electrical-task')
    p=sub.add_parser('verify');p.add_argument('out');a=parser.parse_args()
    result=verify(a.out) if a.command=='verify' else run(a.plan,a.original_run,a.task,a.catalogue,a.target,a.out,electrical_task=a.electrical_task)
    print(json.dumps(result,indent=2));return 0 if a.command=='verify' else 2


if __name__=='__main__':raise SystemExit(main())
