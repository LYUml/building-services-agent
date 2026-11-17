"""Thin source-bound workflow adapter around the existing common-data exporter."""
from pathlib import Path

from ..cli import digest
from ..module_contract import read_json
from .context import load
from .module_bridge import export, methods, project_result, verify

CAPABILITIES = {'analysis.air.classified-allocation', 'analysis.electrical.single-phase-circuits'}


def context(root, plan):
    from ..workflow import local_path
    return load(local_path(Path(root).resolve(), plan.get('project_context')))


def parent_task(task, tasks):
    parent = next((t for t in tasks if t['id'] == task.get('depends_on')), None)
    if parent is None or parent['kind'] != 'module_analysis' or parent.get('depends_on'):
        raise ValueError('Common data requires an earlier explicit numerical module producer')
    return parent


def inputs(root, plan, task, earlier):
    from ..workflow import local_path
    if set(task)-{'id', 'kind', 'depends_on', 'requires_pass', 'description', 'include_inputs'}:
        raise ValueError('Common data inherits its exact producer; replacement inputs forbidden')
    if 'include_inputs' in task and type(task['include_inputs']) is not bool:
        raise ValueError('Input catalogue selection must be boolean')
    parent = parent_task(task, earlier)
    declared = context(root, plan)
    request = read_json(local_path(root, parent['request']))
    if request['capability'] not in CAPABILITIES:
        raise ValueError('Supported common-data analysis capability required')
    if any(request[k] != declared[k] for k in ('project_id', 'scenario_id')):
        raise ValueError('Producer project/scenario differs from explicit project context')
    from ..workspace import ROOT
    return {local_path(root, plan['project_context']), ROOT/'src/bsa/workflow.py',
            ROOT/'src/bsa/workflow_modules.py', *[ROOT/p for p in methods()]}


def source_path(run, task, tasks):
    from ..workflow_modules import result_path
    return result_path(run, parent_task(task, tasks))


def run(root, plan, task, run_directory):
    source = source_path(run_directory, task, plan['tasks'])
    verify_parent_identity(root, plan, task, source)
    declared = context(root, plan)
    model = project_result(source)
    if any(model[k] != declared[k] for k in ('project_id', 'scenario_id')):
        raise ValueError('Completed producer context differs from original plan')
    return export(source, Path(run_directory)/task['id'], include_inputs=task.get('include_inputs', False))


def verify_parent_identity(root, plan, task, source):
    from ..workflow import local_path
    from ..modules import verify_result
    producer = parent_task(task, plan['tasks'])
    request = local_path(root, producer['request'])
    result = verify_result(source)
    if Path(result['request']['path']).resolve() != request or result['request']['sha256'] != digest(request):
        raise ValueError('Producer request differs from the declared source task')


def verify_outputs(root, plan, run_directory, states, input_hashes=None):
    for index, task in enumerate(plan['tasks']):
        if task['kind'] != 'engineering_data' or task['id'] not in states:
            continue
        if input_hashes is not None:
            required = inputs(root, plan, task, plan['tasks'][:index])
            if any(input_hashes.get(str(p)) != digest(p) for p in required):
                raise ValueError('Common-data workflow lost context or method input pins')
        folder = Path(run_directory)/task['id']
        status = states[task['id']]['status']
        if not folder.exists():
            if status == 'pass':
                raise ValueError('Passing common-data task has no output')
            continue
        if status != 'pass' or states[task['depends_on']]['status'] != 'pass':
            raise ValueError('Common-data output contradicts workflow/producer status')
        checked = verify(folder)
        expected_version = 'bsa.engineering-data-export/2' if task.get('include_inputs', False) else 'bsa.engineering-data-export/1'
        if read_json(folder/'receipt.json')['schema'] != expected_version:
            raise ValueError('Common-data input catalogue selection differs from original task')
        source = source_path(run_directory, task, plan['tasks']).resolve()
        verify_parent_identity(root, plan, task, source)
        from .module_bridge import reference
        if checked['source_result'] != reference(source):
            raise ValueError('Common-data source is not the declared workflow producer')
        model = read_json(folder/'model.json')
        declared = context(root, plan)
        if any(model[k] != declared[k] for k in ('project_id', 'scenario_id')):
            raise ValueError('Saved common-data identity differs from original project context')
