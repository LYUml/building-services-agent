"""Independently replay a catalogue recovery receipt and its original failure."""
from pathlib import Path
from . import catalogue_iteration as iteration,circular_fan_selection as selection
from . import delivery,modules,workflow,workflow_status
from .cli import digest
from .engine import ProjectError
from .module_contract import read_json
from .workspace import allowed


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected recovery workspace required')
    result=read_json(folder/'iteration.json')
    if result.get('schema')!='bsa.catalogue-iteration/1' or result.get('scope')!=iteration.SCOPE or result.get('design_accepted') is not False or result.get('original_inputs_unchanged') is not True:
        raise ValueError('Unaccepted unchanged recovery receipt required')
    if not result.get('inputs') or any(not allowed(Path(p)) or not Path(p).is_file() or digest(Path(p))!=sha for p,sha in result['inputs'].items()):
        raise ValueError('Recovery source or method changed')
    artifacts={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file() and p!=folder/'iteration.json'}
    if result.get('artifacts')!=artifacts:raise ValueError('Recovery artifact inventory changed')
    plan,original,catalogue,target=[Path(result[key]).resolve() for key in ('plan','original_run','catalogue','target_plan')]
    if not all(allowed(p) for p in (plan,original,catalogue,target)):raise ValueError('Recovery source workspace changed')
    source,report,integrity=delivery.context(plan,original)
    if not integrity['integrity_pass']:raise ValueError('Original workflow is stale')
    task=result['task'];tasks={t['id']:t for t in source['tasks']}
    diagnosis=workflow_status.diagnose(plan,original)
    if task not in diagnosis['recovery_schedule']['ready_tasks'] or report['tasks'][task]['status']!='fail':raise ValueError('Recovery original is not a ready failure')
    if result.get('original_requirements')!=source['requirements'] or result.get('original_unresolved_inputs')!=source.get('unresolved_inputs',[]):raise ValueError('Recovery removed original requirements or inputs')
    pressure=original/tasks[task]['depends_on'];old_catalogue=workflow.local_path(plan.parent,tasks[task]['catalogue'])
    if digest(old_catalogue)==digest(catalogue):raise ValueError('Recovery catalogue was not revised')
    project,_,inputs,_,options,mechanical=selection.context(pressure,old_catalogue)
    def evaluate(row,name):
        try:
            fresh,_=selection.circular_fan.solve(project,row['curve'])
            actual={key:fresh.get(key) for key in ('status','calculated_checks_pass','checks','operating_point')}
        except ProjectError as exc:actual=dict(status='unsupported',calculated_checks_pass=False,reason=str(exc))
        return selection.shared.eligibility(actual,mechanical.get(row['id']))
    replay=selection.shared.screen(options,evaluate)
    old=read_json(original/task/'fan-selection.json');baseline=read_json(folder/'baseline-recheck/fan-selection.json')
    if replay['selected'] is not None or replay['calculated_checks_pass'] is not False or any(record.get('selected') is not None or record.get('calculated_checks_pass') is not False or iteration.baseline_signature(record)!=iteration.baseline_signature(replay) for record in (old,baseline)):
        raise ValueError('Original failure cannot be reconstructed')
    required={**report['inputs'],**inputs,str(plan):digest(plan),str(original/'workflow.json'):digest(original/'workflow.json')}
    required.update({str(original/name):sha for name,sha in report['artifact_hashes'].items()})
    _,_,replacement_inputs,_,_,_=selection.context(pressure,catalogue);required.update(replacement_inputs)
    for module in (iteration,delivery,modules,workflow,workflow_status,selection):
        required[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    if any(result['inputs'].get(p)!=sha for p,sha in required.items()):raise ValueError('Recovery omitted original source or method pins')
    if digest(target)!=result.get('target_plan_sha256') or read_json(target)!=iteration.revised_plan(source,task,catalogue,target):raise ValueError('Recovery changed more than the declared catalogue')
    if result.get('stages')!=dict(baseline='failure_reproduced',plan='materialized_verified',requirements='completed',workflow='executed',diagnosis='source_verified') or result.get('stage_errors'):
        raise ValueError('Recovery execution stages are incomplete')
    inventory=modules.verify_result(folder/'requirements/result.json')
    if inventory['execution']['status']!='completed':raise ValueError('Recovery requirements inventory is incomplete')
    fresh=workflow_status.diagnose(target,folder/'workflow')
    saved=read_json(folder/'workflow/workflow.json')
    if saved['requirements_inventory']['result']!=str(folder/'requirements/result.json'):raise ValueError('Recovery replaced fresh requirements inventory')
    if fresh!=read_json(folder/'diagnosis.json'):raise ValueError('Recovery diagnosis changed')
    expected='needs_engineering_review' if fresh['execution_pass'] else 'execution_incomplete'
    if result.get('status')!=expected:raise ValueError('Recovery status differs from execution')
    if next(row for row in fresh['tasks'] if row['id']==task)['status']=='pass':
        selection.selected_input(folder/'workflow'/task,folder/'workflow'/tasks[task]['depends_on'],catalogue)
    return dict(integrity_pass=True,original_failure_reproduced=True,
        requirements_preserved=True,recovery_schedule=fresh['recovery_schedule'],
        task_status=saved['tasks'][task]['status'],design_accepted=False)


if __name__=='__main__':
    import argparse
    import json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder')
    print(json.dumps(verify(parser.parse_args().folder),indent=2))
