"""Thin recorded-native source-power audit provider; never a new photometric solver."""
import json
from pathlib import Path
import tempfile
import subprocess

from ..lighting_audit import calculate as engine,runtime,report as reporter
from ..module_contract import read_json,validate
from ..source_refs import file_hash
from ..workspace import ROOT

CAPABILITY='analysis.lighting.source-power-audit'
PAYLOAD='bsa.lighting-source-audit/1'
DESCRIPTION=dict(id='bsa.lighting-source-power',version='1',license='NOASSERTION')
ACCEPTANCE_SCOPE='Recorded native/source input audit only; no fresh lighting simulation, native geometry, circuit ratings or statutory acceptance'
ROLES={'project','layout','design','native_metrics','native_report','area_evidence'}


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!=ROLES:
        raise ValueError('Exact lighting source-audit capability and source roles required')


def external_inputs():return runtime.external_inputs()


def methods():
    files=[*Path(engine.__file__).parent.glob('*.py'),engine.PROJECT_SCHEMA,ROOT/'src/bsa/source_refs.py',ROOT/'src/bsa/engineering_data/model.py']
    return {str(p):file_hash(p) for p in files}


def sources(paths):
    data={role:read_json(path) for role,path in paths.items() if role!='native_report'}
    project=engine.validate_project(data.pop('project'))
    hashes={role:file_hash(path) for role,path in paths.items()}
    engine.verify_sources(project,data,hashes)
    return project,data,hashes


def common(request,data,folder):
    return validate(dict(data,schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],
        units=dict(power='W electrical',density='W electrical/m2',area='m2',illuminance='lx'),
        report=dict(path='analysis/audit.json',sha256=file_hash(folder/'audit.json')),
        native_summary=dict(path='analysis/native-summary.json',sha256=file_hash(folder/'native-summary.json'))))


def execute(request,paths,host_runtime,out):
    pins=methods()
    try:
        try:_,_,external=runtime.configuration()
        except (ValueError,OSError,subprocess.SubprocessError) as exc:
            return dict(status='unavailable',diagnostics=[dict(code='lighting_reader_unavailable',message=str(exc))],payload=None,pins=pins)
        pins.update(external)
        project,_,hashes=sources(paths)
        folder=out/'analysis';folder.mkdir()
        summary,external=runtime.read_summary(paths['native_report'],project['summary_pages'],project['expected_header'],folder/'native')
        pins.update(external)
        data=engine.calculate(project,summary)
        for name,value in [('native-summary.json',summary),('audit.json',data)]:
            (folder/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        (folder/'audit.html').write_text(reporter.render(data),encoding='utf-8')
        if any(file_hash(paths[role])!=sha for role,sha in hashes.items()):raise ValueError('Lighting source changed during audit')
        return dict(status='completed',diagnostics=[],payload=common(request,data,folder),pins=pins)
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError,subprocess.SubprocessError) as exc:
        return dict(status='failed',diagnostics=[dict(code='lighting_source_audit_failed',message=str(exc))],payload=None,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    request_path=Path(result['request']['path']);request=read_json(request_path)
    paths={role:(request_path.parent/r['path']).resolve() for role,r in request['sources'].items()}
    project,_,_=sources(paths);folder=Path(result_path).parent/'analysis'
    with tempfile.TemporaryDirectory(dir=Path(result_path).parent.parent) as scratch:
        summary,external=runtime.read_summary(paths['native_report'],project['summary_pages'],project['expected_header'],Path(scratch)/'native')
        for name,sha in {**methods(),**external}.items():
            if result['inputs'].get(name)!=sha:raise ValueError('Lighting reader/source method pin missing or changed')
        retained=read_json(folder/'native-summary.json')
        # PDF copy identifiers can differ; the original source/page and parsed facts cannot.
        observed=dict(summary);expected=dict(retained)
        observed.pop('excerpt_sha256');expected.pop('excerpt_sha256')
        if observed!=expected:raise ValueError('Retained native summary differs from source replay')
    data=engine.calculate(project,retained)
    if read_json(folder/'audit.json')!=data or (folder/'audit.html').read_text(encoding='utf-8')!=reporter.render(data) or common(request,data,folder)!=result['payload']:
        raise ValueError('Lighting calculation/report differs from bound source inputs')
