"""Host-selected selective replay composed with the original workflow runner."""
from pathlib import Path

from ..module_contract import read_json
from ..source_refs import file_hash, reference, resolve_reference
from ..workspace import ROOT
from . import core


def pins(checkpoint):
    checkpoint=Path(checkpoint).resolve()
    receipt,*_=core.load(checkpoint)
    return {*(checkpoint/name for name in ['receipt.json',*receipt['artifacts']]),
            resolve_reference(receipt['workflow']),*[ROOT/p for p in core.methods()],
            ROOT/'src/bsa/workflow.py',ROOT/'src/bsa/delivery.py'}


def prepare(checkpoint,plan):
    assessed=core.impact(checkpoint,plan=plan)
    if not assessed['plan_valid']:raise ValueError('Valid current plan required for selective replay')
    return dict(schema='bsa.workflow-reuse/1',checkpoint=reference(Path(checkpoint)/'receipt.json'),
                assessment=assessed,reused_tasks=[],design_accepted=False)


def eligible(record,task,provider,disabled,module_runtime):
    return (not any(value is not None for value in module_runtime.values()) and provider not in disabled and provider==task.get('provider') and
        task['kind']=='module_analysis' and not task.get('depends_on') and
        record['assessment']['tasks'].get(task['id'],{}).get('reuse_eligible',False))


def copy(record,task,plan,out):
    checkpoint=resolve_reference(record['checkpoint']).parent
    core.reuse(checkpoint,task['id'],Path(out)/'_reuse'/task['id'],plan=plan,module_out=Path(out)/task['id'])
    record['reused_tasks'].append(task['id'])
    return read_json(Path(out)/task['id']/'result.json')


def verify(record,plan,out,states,input_hashes=None):
    out=Path(out).resolve()
    if record is None:
        for p in (out/'_reuse').glob('*/receipt.json'):
            try:data=read_json(p)
            except ValueError:continue  # unrelated legacy task may use this directory name
            if isinstance(data,dict) and data.get('schema')=='bsa.module-reuse/2':
                raise ValueError('Reuse evidence lost its declared workflow selection')
        return
    if set(record)!={'schema','checkpoint','assessment','reused_tasks','design_accepted'} or record['schema']!='bsa.workflow-reuse/1' or record['design_accepted'] is not False:
        raise ValueError('Exact unaccepted workflow reuse selection required')
    checkpoint=resolve_reference(record['checkpoint']).parent
    if record['assessment']!=core.impact(checkpoint,plan=plan):raise ValueError('Workflow reuse assessment drifted')
    if input_hashes is not None and any(input_hashes.get(str(p))!=file_hash(p) for p in pins(checkpoint)):
        raise ValueError('Workflow lost checkpoint or reuse-method pins')
    ids=record['reused_tasks']
    if not isinstance(ids,list) or len(ids)!=len(set(ids)) or any(not isinstance(i,str) for i in ids):
        raise ValueError('Unique declared reused tasks required')
    if (out/'_reuse').exists() and {p.name for p in (out/'_reuse').iterdir()}!=set(ids):
        raise ValueError('Reuse evidence inventory differs from workflow selection')
    for task_id in ids:
        if states.get(task_id,{}).get('kind')!='module_analysis' or states[task_id]['status']!='pass':
            raise ValueError('Reused numerical task is not passing in this workflow')
        folder=out/'_reuse'/task_id
        if any(p!=p.resolve() for p in (out/task_id,folder)):
            raise ValueError('Canonical workflow reuse folders traverse a link or junction')
        core.verify_reuse(folder)
        data=read_json(folder/'receipt.json')
        if data['schema']!='bsa.module-reuse/2' or data['impact']!=record['assessment'] or data['module_result']!=reference(out/task_id/'result.json'):
            raise ValueError('Reuse provenance does not bind the canonical workflow task')
