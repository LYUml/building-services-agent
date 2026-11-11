"""Bind an exact verified requirements inventory to its existing engineering plan."""
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .modules import verify_result


def bind(plan,result_path):
    plan,result_path=Path(plan).resolve(),Path(result_path).resolve()
    result=verify_result(result_path)
    if result['execution']['status']!='completed' or result['payload_schema']!='bsa.requirements-inventory/1':
        raise ValueError('Completed verified requirements inventory required')
    request_path=Path(result['request']['path']);request=read_json(request_path)
    if (request_path.parent/request['sources']['plan']['path']).resolve()!=plan:
        raise ValueError('Requirements inventory must reference the exact execution plan')
    payload=result['payload']
    if payload['source_plan_sha256']!=digest(plan):raise ValueError('Requirements inventory plan changed')
    pins=dict(result['inputs']);pins[str(result_path)]=digest(result_path)
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    pins.update({str((result_path.parent/name).resolve()):sha for name,sha in result['artifacts'].items()})
    record=dict(result=str(result_path),sha256=digest(result_path),source_plan=str(plan),source_plan_sha256=digest(plan),
        requirement_ids=[r['id'] for r in payload['requirements']],
        interpretation_status='not_assessed',design_accepted=False)
    return record,pins


def verify_report(report,plan=None):
    record=report.get('requirements_inventory')
    if record is None:
        if str(Path(__file__).resolve()) in report['inputs']:raise ValueError('Workflow lost its pinned requirements inventory record')
        return {}
    expected,pins=bind(plan if plan is not None else record['source_plan'],record['result'])
    if expected!=record or any(report['inputs'].get(p)!=sha for p,sha in pins.items()):
        raise ValueError('Workflow requirements inventory lineage differs')
    payload=verify_result(record['result'])['payload']
    requirements=[{k:row.get(k) for k in original} for row,original in zip(report['requirements'],payload['requirements'])]
    if len(report['requirements'])!=len(payload['requirements']) or requirements!=payload['requirements']:
        raise ValueError('Workflow requirement matrix differs from inventory')
    if {k:v['kind'] for k,v in report['tasks'].items()}!={r['id']:r['kind'] for r in payload['tasks']}:
        raise ValueError('Workflow task identities differ from requirements inventory')
    if report.get('unresolved_inputs',[])!=payload['unresolved_inputs']:
        raise ValueError('Workflow unresolved inputs differ from requirements inventory')
    return pins
