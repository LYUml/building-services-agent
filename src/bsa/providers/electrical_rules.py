"""Trusted dispatch adapter around the existing whole-path electrical jurisdiction consumer."""
from pathlib import Path
from ..cli import digest
from ..module_contract import read_json

CAPABILITY='regulation.electrical.radial-paths'
PAYLOAD='bsa.rule-assessment/1'
DESCRIPTION=dict(id='bsa.electrical-path-rules',version='1',license='NOASSERTION')
ACCEPTANCE_SCOPE='Selected radial whole-path voltage-drop rules only;scope,edition,products and whole engineering/regulatory acceptance remain separate'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'producer','topology','basis','pack'}:
        raise ValueError('Electrical rule provider requires exact producer/topology/basis/pack sources')


def execute(request,paths,runtime,out):
    from .. import module_electrical_rules as rules
    from ..modules import ROOT,verify_result
    pins={str(Path(rules.__file__).resolve()):digest(Path(rules.__file__))}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    if not runtime.get('sources'):return outcome('unavailable','source_cache_not_configured','Explicit host official-source cache path required')
    sources=Path(runtime['sources']).resolve()
    if not sources.is_relative_to(ROOT):raise ValueError('Repository-local official-source cache required')
    try:
        producer=verify_result(paths['producer'])
        if any(request[k]!=producer[k] for k in ('project_id','scenario_id')):
            raise ValueError('Rule request project/scenario differs from producer')
        if producer['payload'] is None or producer['payload']['coordinate_frame']!=request['coordinate_frame']:
            raise ValueError('Rule request frame differs from producer')
        report=rules.run(paths['producer'],paths['topology'],paths['basis'],paths['pack'],sources,out/'rules')
        rules.verify(out/'rules');pins.update(report['inputs'])
    except (ValueError,OSError,KeyError) as exc:return outcome('failed','rule_evaluation_failed',str(exc))
    return dict(status='completed',diagnostics=[],payload=report['assessment'],pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    from ..module_electrical_rules import verify
    request_path=Path(result['request']['path']);request=read_json(request_path)
    paths={k:(request_path.parent/v['path']).resolve() for k,v in request['sources'].items()}
    report=verify(Path(result_path).parent/'rules')
    from ..modules import verify_result
    producer=verify_result(paths['producer'])
    if any(request[k]!=producer[k] for k in ('project_id','scenario_id')):raise ValueError('Rule provider project/scenario differs')
    if any(Path(report[k]).resolve()!=paths[k if k!='producer_result' else 'producer'] for k in ('producer_result','topology','basis','pack')):
        raise ValueError('Rule provider source correspondence differs')
    if any(result['inputs'].get(p)!=sha for p,sha in report['inputs'].items()) or report['assessment']!=result['payload']:
        raise ValueError('Rule provider evidence differs')
