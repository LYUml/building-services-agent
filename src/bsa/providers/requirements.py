"""Common inventory of source-linked host requirements;never infer source meaning."""
from pathlib import Path
from ..cli import digest
from ..module_contract import read_json

CAPABILITY='requirements.source-inventory'
PAYLOAD='bsa.requirements-inventory/1'
DESCRIPTION=dict(id='bsa.source-requirements',version='1',license='NOASSERTION')
ACCEPTANCE_SCOPE='Exact source passages,declared obligations and unresolved inputs only;semantic completeness,design and engineering acceptance remain unassessed'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'plan'}:
        raise ValueError('Requirements provider requires exact source-linked plan')


def inventory(request,plan_path):
    from ..workflow import validate_plan,plan_documents
    from ..modules import ROOT
    plan_path=Path(plan_path).resolve();plan,inputs=validate_plan(plan_path)
    methods={ROOT/'src/bsa'/n for n in ('workflow.py','documents.py','engine.py','cli.py')}
    pins={str(p.resolve()):digest(p) for p in {*inputs,plan_path,*methods}}
    documents=plan_documents(plan_path.parent,plan)
    payload=dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],source_plan_sha256=digest(plan_path),
        documents=[dict(id=f'D{i:03}',path=row['brief'],sha256=row['brief_sha256'],role='primary' if i==1 else 'supplement_or_reference')
                   for i,row in enumerate([plan,*plan.get('supplemental_briefs',[])],1)],
        passages=[dict(id=row['id'],text=row['text'],locator={k:v for k,v in row.items() if k not in ('id','text')},
                       disposition=plan['passage_dispositions'][row['id']]) for row in documents['passages']],
        requirements=plan['requirements'],tasks=plan['tasks'],unresolved_inputs=plan.get('unresolved_inputs',[]),
        interpretation_status='not_assessed',engineering_execution='not_executed',geometry_bound=False,design_accepted=False)
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Requirements source changed during inventory')
    return payload,pins


def execute(request,paths,runtime,out):
    try:payload,pins=inventory(request,paths['plan'])
    except (ValueError,OSError,KeyError) as exc:
        return dict(status='failed',diagnostics=[dict(code='requirements_source_invalid',message=str(exc))],payload=None,pins={})
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    request_path=Path(result['request']['path']);request=read_json(request_path)
    payload,pins=inventory(request,(request_path.parent/request['sources']['plan']['path']).resolve())
    if result['payload']!=payload or any(result['inputs'].get(p)!=sha for p,sha in pins.items()):
        raise ValueError('Requirements inventory differs from complete source replay')
