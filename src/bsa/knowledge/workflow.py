"""Thin existing-workflow/MCP composition; no second retrieval engine."""
import json
from pathlib import Path

from ..module_contract import read_json
from ..source_refs import file_hash, reference, resolve_reference
from ..workspace import ROOT
from . import index
from .manifest import load
from .sources import project_context

KINDS = {'knowledge_index', 'knowledge_query'}
SCOPE = 'Source-bound knowledge lookup only; matching is not applicability or engineering acceptance'


def manifest_inputs(path):
    manifest = load(path)
    files = {Path(path).resolve(), *[ROOT/p for p in index.methods()]}
    if manifest['project_context'] is not None:
        files.add(resolve_reference(manifest['project_context']))
    for row in manifest['sources']:
        if row['kind'] == 'git_reference':
            from .sources import passages
            passages(row, project_context(manifest))  # immutable, bounded Git blob read
            continue
        source = resolve_reference(row['source'])
        files.add(source)
        if row['kind'] == 'project_inputs':
            from ..engineering_data.module_bridge import verify
            from ..modules import verify_result
            checked = verify(source.parent)
            files.update(source.parent.iterdir())
            producer = resolve_reference(checked['source_result'])
            result = verify_result(producer)
            files.add(producer)
            files.update(Path(p) for p in result['inputs'])
            files.update(producer.parent/p for p in result['artifacts'])
    return files


def producer(task, earlier):
    parent = next((t for t in earlier if t['id'] == task.get('depends_on')), None)
    if parent is None or parent['kind'] != 'knowledge_index':
        raise ValueError('Knowledge query requires an earlier knowledge index producer')
    return parent


def selected(root, task, earlier, run_directory=None):
    from ..workflow import local_path
    if task['kind'] == 'knowledge_index':
        return local_path(root, task.get('manifest')), None
    if bool(task.get('depends_on')) == bool(task.get('index_receipt')):
        raise ValueError('Knowledge query needs exactly one earlier index or explicit saved index receipt')
    if task.get('depends_on'):
        parent = producer(task, earlier)
        return local_path(root, parent.get('manifest')), Path(run_directory)/parent['id'] if run_directory is not None else None
    receipt = local_path(root, task['index_receipt'])
    if receipt.name != 'receipt.json':
        raise ValueError('Explicit saved index receipt.json required')
    index.verify(receipt.parent)
    return resolve_reference(read_json(receipt)['manifest']), receipt.parent


def query_arguments(root, plan, task):
    from ..workflow import local_path
    options = task.get('query')
    if not isinstance(options, dict) or 'text' not in options or set(options)-{'text','role','discipline','jurisdiction','limit','include_project_facts'}:
        raise ValueError('Explicit bounded knowledge query options required')
    args = dict(options)
    if options.get('include_project_facts') or options.get('role') == 'project_input':
        args['expected_context'] = local_path(root, plan.get('project_context'))
    return args


def inputs(root, plan, task, earlier):
    common = {'id','kind','description','requires_pass'}
    extra = {'manifest'} if task['kind'] == 'knowledge_index' else {'query','depends_on','index_receipt'}
    if set(task)-common-extra:
        raise ValueError('Knowledge task contains replacement inputs or unsupported fields')
    manifest_path, folder = selected(root, task, earlier)
    files = manifest_inputs(manifest_path) | {ROOT/'src/bsa/workflow.py'}
    if folder is not None:
        files.update(folder.iterdir())
    corpus = project_context(load(manifest_path))
    if corpus is not None:
        from ..engineering_data.context import load as load_context
        from ..workflow import local_path
        context_path = local_path(root, plan.get('project_context'))
        declared = load_context(context_path)
        if any(corpus[k] != declared[k] for k in ('project_id','scenario_id')):
            raise ValueError('Knowledge corpus context differs from workflow project/scenario')
        files.add(context_path)
    if task['kind'] == 'knowledge_query':
        args = query_arguments(root, plan, task)
        if folder is not None:
            index.query(folder, **args)  # reuse exact validation for a saved index
    return files


def run(root, plan, task, run_directory):
    manifest_path, source = selected(root, task, plan['tasks'], run_directory)
    folder = Path(run_directory)/task['id']
    if task['kind'] == 'knowledge_index':
        index.build(manifest_path, folder)
    else:
        result = index.query(source, **query_arguments(root, plan, task))
        folder.mkdir()
        (folder/'query.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return dict(scope=SCOPE, design_accepted=False)


def facts(result):
    result = dict(result)
    del result['sql_seconds']  # observation only; every citation/value is compared
    return result


def verify_outputs(root, plan, run_directory, states, input_hashes=None):
    for position, task in enumerate(plan['tasks']):
        if task['kind'] not in KINDS or task['id'] not in states:
            continue
        if input_hashes is not None:
            required = inputs(root, plan, task, plan['tasks'][:position])
            if any(input_hashes.get(str(p)) != file_hash(p) for p in required):
                raise ValueError('Knowledge workflow lost source, context or method pins')
        folder = Path(run_directory)/task['id']
        status = states[task['id']]['status']
        if not folder.exists():
            if status == 'pass':
                raise ValueError('Passing knowledge task has no output')
            continue
        if status != 'pass':
            if status == 'fail':
                continue  # retain partial failure evidence; never promote it to an index
            raise ValueError('Knowledge output contradicts workflow status')
        manifest_path, source = selected(root, task, plan['tasks'][:position], run_directory)
        if task['kind'] == 'knowledge_index':
            index.verify(folder)
            if read_json(folder/'receipt.json')['manifest'] != reference(manifest_path):
                raise ValueError('Knowledge index differs from declared workflow manifest')
        else:
            if task.get('depends_on') and states[task['depends_on']]['status'] != 'pass':
                raise ValueError('Knowledge query upstream index did not pass')
            if {p.name for p in folder.iterdir()} != {'query.json'} or (folder/'query.json').is_symlink():
                raise ValueError('Exact regular-file knowledge query output required')
            actual = read_json(folder/'query.json')
            if facts(actual) != facts(index.query(source, **query_arguments(root, plan, task))):
                raise ValueError('Saved knowledge query differs from declared query and original sources')
