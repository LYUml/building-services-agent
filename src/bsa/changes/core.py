"""Reuse existing workflow receipts/provider verifiers, never transfer acceptance."""
import json
from pathlib import Path
import re
import shutil
import sys

from ..module_contract import read_json
from ..source_refs import file_hash, reference, resolve_reference
from ..workspace import ROOT, allowed, intake_output

SCHEMA = 'bsa.change-checkpoint/2'
SCOPE = 'Declared source/method/artifact correspondence and conservative dependencies; no engineering acceptance or authenticated provenance'
VERIFICATION = 'Original module verifier passed before and after byte-preserving copy'
REUSABLE_PROVIDERS={'bsa.single-phase-circuits','bsa.classified-air-allocation'}


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def methods():
    files=[*Path(__file__).parent.glob('*.py'),ROOT/'src/bsa/source_refs.py',ROOT/'src/bsa/workspace.py',ROOT/'src/bsa/doctor.py']
    files.extend(ROOT/'src/bsa/engineering_data'/name for name in ('inputs.py','quantities.py','model.py'))
    return {p.relative_to(ROOT).as_posix():file_hash(p) for p in sorted(files)}


def environment(providers):
    from ..doctor import check
    extras=['modules']+(['spatial'] if 'bsa.classified-air-allocation' in providers else [])
    inspected=check(extras=extras)
    return dict(python=sys.version,python_binary_sha256=file_hash(sys.executable),
        requirements_sha256=file_hash(ROOT/'pyproject.toml'),packages=inspected['packages'],
        ready=inspected['status']=='direct_requirements_ready',
        scope='Selected direct pinned distribution versions and Python binary; in-place transitive package edits are not authenticated')


def checkpoint(run, out):
    from ..workflow import verify
    run, out = Path(run).resolve(), Path(out).resolve()
    if not allowed(run) or not intake_output(out) or out.exists() or out.is_relative_to(run) or run.is_relative_to(out):
        raise ValueError('Fresh checkpoint separate from original workflow required')
    checked = verify(run)
    if not checked['integrity_pass']:
        raise ValueError('Current source-bound workflow required before taking a checkpoint')
    report_path = run/'workflow.json'
    report = read_json(report_path)
    source = report.get('source_plan')
    if not source:
        raise ValueError('Explicit original workflow plan required')
    plan = Path(source['path']).resolve()
    if not allowed(plan) or file_hash(plan) != source['sha256'] or out == plan or out in plan.parents:
        raise ValueError('Unchanged original plan and separate checkpoint required')
    plan_data=read_json(plan)
    context=None
    if plan_data.get('project_context'):
        from ..workflow import local_path
        from ..engineering_data.context import load as load_context
        context_path=local_path(plan.parent,plan_data['project_context'])
        if {**report['inputs'],**report.get('runtime_inputs',{})}.get(str(context_path))!=file_hash(context_path):
            raise ValueError('Declared project context must be pinned by the original workflow')
        context=load_context(context_path)
    from ..modules import verify_result
    selected=[]
    for task in plan_data['tasks']:
        name=task['id']+'/result.json'
        if task['kind']=='module_analysis' and not task.get('depends_on') and name in report['artifact_hashes']:
            result=verify_result(run/name)
            if context and any(result[k]!=context[k] for k in ('project_id','scenario_id')):
                raise ValueError('Numerical module differs from declared project/scenario context')
            selected.append((task,name))
    runtime=environment({read_json(run/name)['provider']['id'] for _,name in selected})
    if not runtime['ready']:
        raise ValueError('Pinned numerical dependency profile must be ready before checkpointing')
    out.mkdir(parents=True)
    (out/'plan.json').write_bytes(plan.read_bytes())
    (out/'workflow.json').write_bytes(report_path.read_bytes())
    for task,name in selected:
        (out/('module-'+task['id']+'.json')).write_bytes((run/name).read_bytes())
        from .parameters import PROVIDERS,capture
        result=read_json(run/name)
        if result['provider']['id'] in PROVIDERS:capture(result,task['id'],out)
    files = {p.name:file_hash(p) for p in out.iterdir()}
    receipt = dict(schema=SCHEMA, workflow=reference(report_path), source_plan=reference(plan),
        artifacts=files, methods=methods(), runtime=runtime, scope=SCOPE, design_accepted=False)
    write(out/'receipt.json',receipt)
    load(out)
    return receipt


def load(folder):
    folder = Path(folder).resolve()
    if not intake_output(folder):
        raise ValueError('Checkpoint outside selected workspace')
    receipt = read_json(folder/'receipt.json')
    if set(receipt)!={'schema','workflow','source_plan','artifacts','methods','runtime','scope','design_accepted'} or receipt['schema'] not in ('bsa.change-checkpoint/1',SCHEMA) or receipt['scope']!=SCOPE or receipt['design_accepted'] is not False:
        raise ValueError('Exact unaccepted change checkpoint required')
    # The old plan may change; the original workflow record must remain intact.
    original = resolve_reference(receipt['workflow'])
    report = read_json(original)
    if file_hash(folder/'workflow.json') != receipt['workflow']['sha256']:
        raise ValueError('Checkpoint workflow archive differs from original record')
    plan = read_json(folder/'plan.json')
    if file_hash(folder/'plan.json') != receipt['source_plan']['sha256'] or report['source_plan']['sha256'] != receipt['source_plan']['sha256']:
        raise ValueError('Archived plan differs from original workflow identity')
    # Validate the normalized source-plan path without requiring its old bytes.
    spec = dict(receipt['source_plan'])
    if spec['workspace'] not in ('tool','project') or not isinstance(spec['path'],str) or '\\' in spec['path'] or ':' in spec['path'] or any(x in ('','.','..') for x in spec['path'].split('/')):
        raise ValueError('Normalized original source plan required')
    from ..workspace import project_root
    base = ROOT if spec['workspace']=='tool' else project_root()
    if base is None:
        raise ValueError('Original project workspace unavailable')
    original_plan = (base/spec['path']).resolve()
    if not original_plan.is_relative_to(base) or not allowed(original_plan) or str(original_plan)!=report['source_plan']['path']:
        raise ValueError('Original plan path differs from saved workflow')
    expected = {'plan.json','workflow.json'}
    modules = {}
    ids = set()
    for task in plan['tasks']:
        name = task.get('id')
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',name) or name in ids:
            raise ValueError('Unique path-safe archived task IDs required')
        ids.add(name)
        key = name+'/result.json'
        if task['kind']=='module_analysis' and not task.get('depends_on') and key in report['artifact_hashes']:
            archive = 'module-'+name+'.json'
            expected.add(archive)
            if file_hash(folder/archive) != report['artifact_hashes'][key]:
                raise ValueError('Module archive differs from original workflow artifact')
            modules[name]=read_json(folder/archive)
            from .parameters import PROVIDERS,paths,archived
            if receipt['schema']==SCHEMA and modules[name]['provider']['id'] in PROVIDERS:
                expected.update(paths(name));archived(folder,name,modules[name])
    if set(receipt['artifacts'])!=expected or {p.name for p in folder.iterdir()}!=expected|{'receipt.json'} or any(p.is_symlink() or not p.is_file() for p in folder.iterdir()):
        raise ValueError('Exact regular-file checkpoint inventory required')
    if any(file_hash(folder/name)!=sha for name,sha in receipt['artifacts'].items()):
        raise ValueError('Checkpoint archive changed')
    return receipt, plan, report, modules, original_plan, original.parent


def category(path):
    path=Path(path)
    if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'contracts'):
        return 'method_or_contract'
    return 'source_or_runtime'


def impact(folder, *, plan=None,parameter_offset=0,parameter_limit=50):
    if type(parameter_offset) is not int or parameter_offset<0 or type(parameter_limit) is not int or not 1<=parameter_limit<=100:
        raise ValueError('Bounded parameter pagination required')
    receipt, old_plan, report, modules, original_plan, run = load(folder)
    current_plan = original_plan if plan is None else Path(plan).resolve()
    if not allowed(current_plan) or current_plan.parent!=original_plan.parent:
        raise ValueError('Current plan must remain in the original selected project directory')
    old_inputs={**report['inputs'],**report.get('runtime_inputs',{})}
    global_paths=set(old_inputs)-{str(original_plan)}
    ownership={}
    for task_id, result in modules.items():
        own=set(result['inputs'])
        if all(old_inputs.get(p)==sha for p,sha in result['inputs'].items()):
            ownership[task_id]=own
            global_paths-=own
    if old_plan.get('project_context'):
        global_paths.add(str((original_plan.parent/old_plan['project_context']).resolve()))
    changes=[]
    changed=set()
    for name,before in old_inputs.items():
        path=Path(name)
        after=file_hash(path) if path.is_file() else None
        if before!=after:
            changed.add(name)
            changes.append(dict(path=name,before=before,after=after,kind=category(path)))
    error=None
    current_inputs=set()
    try:
        from ..workflow import validate_plan
        current,current_inputs=validate_plan(current_plan)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        error=str(exc)
        try:current=read_json(current_plan)
        except (ValueError,OSError):current={}
    if not isinstance(current,dict):current={}
    for path in sorted(current_inputs):
        if str(path) not in old_inputs:
            changes.append(dict(path=str(path),before=None,after=file_hash(path),kind='added_'+category(path)))
    current_rows=current.get('tasks',[])
    if not isinstance(current_rows,list):current_rows=[]
    current_tasks={t['id']:t for t in current_rows if isinstance(t,dict) and isinstance(t.get('id'),str)}
    previous={t['id']:t for t in old_plan['tasks']}
    metadata_changed={k:v for k,v in old_plan.items() if k!='tasks'}!={k:v for k,v in current.items() if k!='tasks'}
    detector_changed=receipt['methods']!=methods()
    runtime=environment({result['provider']['id'] for result in modules.values()})
    runtime_changed=receipt['runtime']!=runtime
    recipe_changes={name for name in set(previous)|set(current_tasks) if previous.get(name)!=current_tasks.get(name)}
    rows={}
    for task in old_plan['tasks']:
        name=task['id']; reasons=[]
        parents=list(dict.fromkeys([task[k] for k in ('depends_on','ifc_from','junction_from','connector_from') if task.get(k)]+task.get('requires_pass',[])))
        direct=ownership.get(name,set(old_inputs))
        touched=sorted(changed & (direct|global_paths)-{str(original_plan)})
        if touched:reasons.append('pinned_inputs_changed')
        if metadata_changed:reasons.append('brief_context_or_requirements_changed')
        if detector_changed:reasons.append('change_detector_method_changed')
        if runtime_changed:reasons.append('upstream_environment_changed')
        if error:reasons.append('current_plan_invalid')
        if name in recipe_changes:reasons.append('task_recipe_changed')
        if name not in ownership and recipe_changes:reasons.append('conservative_unknown_task_recipe_impact')
        upstream=[p for p in parents if p not in rows or rows[p]['invalidated']]
        if upstream:reasons.append('upstream_invalidated')
        artifacts=[]
        prefix=name+'/'
        for key,before in report['artifact_hashes'].items():
            if key.startswith(prefix):
                path=run/key
                if not path.is_file() or file_hash(path)!=before:artifacts.append(key)
        if name in modules:
            expected={key[len(prefix):] for key in report['artifact_hashes'] if key.startswith(prefix)}
            actual={p.relative_to(run/name).as_posix() for p in (run/name).rglob('*') if p.is_file()}
            if actual!=expected:artifacts.append(name+'/(inventory changed)')
        if artifacts:reasons.append('artifact_changed')
        result=modules.get(name)
        reusable=bool(not reasons and name in ownership and report['tasks'][name]['status']=='pass' and result['execution']['status']=='completed' and result['provider']['id']==task.get('provider') and result['provider']['id'] in REUSABLE_PROVIDERS)
        rows[name]=dict(kind=task['kind'],invalidated=bool(reasons),reasons=reasons,changed_inputs=touched,
            upstream_invalidated=upstream,changed_artifacts=artifacts,reuse_eligible=reusable,
            reuse_scope='Independent numerical module; original provider verification still required' if reusable else 'Full original execution required or reference-only unchanged artifact',
            design_accepted=False)
        if result is not None:
            from .parameters import PROVIDERS,compare
            if receipt['schema']==SCHEMA and result['provider']['id'] in PROVIDERS and name in current_tasks:
                rows[name]['parameter_changes']=compare(folder,name,result,current_tasks[name],current_plan.parent,offset=parameter_offset,limit=parameter_limit)
            else:rows[name]['parameter_changes']=dict(status='not_recorded',scope='Legacy checkpoint or unsupported primary-input adapter')
    for name in set(current_tasks)-set(previous):
        rows[name]=dict(kind=current_tasks[name]['kind'],invalidated=True,reasons=['new_task'],changed_inputs=[],upstream_invalidated=[],changed_artifacts=[],reuse_eligible=False,design_accepted=False)
    return dict(schema='bsa.change-impact/1',checkpoint=reference(Path(folder)/'receipt.json'),current_plan=reference(current_plan),
        plan_valid=error is None,validation_error=error,changes=changes,tasks=rows,
        upstream_environment=dict(changed=runtime_changed,before=receipt['runtime'],after=runtime),
        scope=SCOPE,limits='Unknown task input ownership uses conservative whole-workflow pins; no automatic plan/source edits or acceptance transfer',design_accepted=False)


def reuse(folder, task_id, out, *, plan=None, module_out=None):
    assessed=impact(folder,plan=plan)
    if not assessed['tasks'].get(task_id,{}).get('reuse_eligible'):
        raise ValueError('Task is invalidated, incomplete or lacks a verified numerical reuse path')
    _,_,report,_,_,run=load(folder)
    source=run/task_id/'result.json'
    from ..modules import verify_result
    verified=verify_result(source)
    if any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in source.parent.rglob('*')):
        raise ValueError('Reuse requires regular source files/directories; no link traversal')
    out=Path(out).resolve()
    if not intake_output(out) or out.exists() or out.is_relative_to(run) or run.is_relative_to(out) or out.is_relative_to(Path(folder).resolve()):
        raise ValueError('Fresh reuse output separate from baseline and checkpoint required')
    detached=module_out is not None
    module=Path(module_out).resolve() if detached else out/'module'
    if detached and (not intake_output(module) or module.exists() or module.is_relative_to(run) or run.is_relative_to(module) or module.is_relative_to(Path(folder).resolve()) or module.is_relative_to(out) or out.is_relative_to(module)):
        raise ValueError('Fresh separate canonical module directory required')
    # Re-check the exact requested provider/source before copying, and verify after.
    pins={str(source):file_hash(source),**verified['inputs']}
    out.mkdir(parents=True)
    shutil.copytree(source.parent,module)
    verify_result(module/'result.json')
    if any(not Path(p).is_file() or file_hash(p)!=sha for p,sha in pins.items()) or impact(folder,plan=plan)!=assessed:
        raise ValueError('Reuse dependencies changed during copying')
    base=module if detached else out
    artifacts={p.relative_to(base).as_posix():file_hash(p) for p in module.rglob('*') if p.is_file()}
    receipt=dict(schema='bsa.module-reuse/2' if detached else 'bsa.module-reuse/1',impact=assessed,source_result=reference(source),artifacts=artifacts,
        verification=VERIFICATION,scope=SCOPE,design_accepted=False)
    if detached:receipt['module_result']=reference(module/'result.json')
    write(out/'receipt.json',receipt)
    verify_reuse(out)
    return receipt


def verify_reuse(out):
    out=Path(out).resolve()
    if not intake_output(out):raise ValueError('Selected reuse workspace required')
    data=read_json(out/'receipt.json')
    detached=data.get('schema')=='bsa.module-reuse/2'
    fields={'schema','impact','source_result','artifacts','verification','scope','design_accepted'}|({'module_result'} if detached else set())
    if set(data)!=fields or data['schema'] not in ('bsa.module-reuse/1','bsa.module-reuse/2') or data['scope']!=SCOPE or data['verification']!=VERIFICATION or data['design_accepted'] is not False:
        raise ValueError('Versioned unaccepted module reuse receipt required')
    inventory={'receipt.json'} if detached else {'module','receipt.json'}
    if {p.name for p in out.iterdir()}!=inventory:raise ValueError('Exact reuse bundle required')
    module=resolve_reference(data['module_result']).parent if detached else out/'module'
    if detached:
        from ..workspace import project_root
        root=ROOT if data['module_result']['workspace']=='tool' else project_root()
        declared=root/data['module_result']['path']
        if declared!=declared.resolve():raise ValueError('Reused module reference traverses a link or junction')
    if detached and (Path(data['module_result']['path']).name!='result.json' or module.is_relative_to(out) or out.is_relative_to(module)):
        raise ValueError('Separate canonical module result required')
    if any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in [module,out/'receipt.json',*module.rglob('*')]):
        raise ValueError('Exact regular-file reuse bundle required')
    assessed=data['impact']
    folder=resolve_reference(assessed['checkpoint']).parent
    plan=resolve_reference(assessed['current_plan'])
    if assessed!=impact(folder,plan=plan):
        raise ValueError('Reuse assessment changed')
    source=resolve_reference(data['source_result'])
    task_id=source.parent.name
    _,_,_,_,_,run=load(folder)
    if source!=run/task_id/'result.json' or not assessed['tasks'].get(task_id,{}).get('reuse_eligible'):
        raise ValueError('Reuse source differs from eligible checkpoint task')
    from ..modules import verify_result
    verify_result(source);verify_result(module/'result.json')
    base=module if detached else out
    expected={p.relative_to(base).as_posix():file_hash(p) for p in module.rglob('*') if p.is_file()}
    if expected!=data['artifacts']:
        raise ValueError('Reused module artifacts changed')
    if any(file_hash(base/name)!=file_hash(source.parent/(Path(name) if detached else Path(name).relative_to('module'))) for name in expected):
        raise ValueError('Reused bytes differ from original source module')
    return dict(integrity_pass=True,files=len(expected),scope=SCOPE,design_accepted=False)
