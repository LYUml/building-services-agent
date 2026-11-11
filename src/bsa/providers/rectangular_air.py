"""Thin provider for the existing rectangular air-tree budget and pinned fluids."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='analysis.air.rectangular-tree'
PAYLOAD='bsa.air-budget/1'
DESCRIPTION=dict(id='fluids.rectangular-air-budget',version='1.3.1',license='MIT')
ACCEPTANCE_SCOPE='Prescribed level constant-density rectangular air-tree budget only;source applicability,K,fan selection,physical geometry,regulations and full design acceptance remain separate'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'project'}:raise ValueError('Rectangular air budget requires exact project source and supported capability')


def execute(request,paths,runtime,out):
    names=('rectangular_network.py','network.py','engine.py','cli.py')
    pins={str(ROOT/'src/bsa'/n):digest(ROOT/'src/bsa'/n) for n in names}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if importlib.metadata.version('fluids')!='1.3.1':return outcome('unavailable','runtime_incompatible','Pinned fluids1.3.1 required')
    except importlib.metadata.PackageNotFoundError:return outcome('unavailable','runtime_missing','fluids1.3.1 is not installed')
    native=out/'analysis'
    try:process=subprocess.run([sys.executable,'-m','bsa.rectangular_network',str(paths['project']),'--out',str(native)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    except OSError as exc:return outcome('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return outcome('failed','provider_timeout',str(exc))
    (out/'provider.stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'provider.stderr.txt').write_text(process.stderr,encoding='utf-8')
    (out/'process.json').write_text(json.dumps(dict(returncode=process.returncode)),encoding='utf-8')
    if process.returncode not in (0,2) or not (native/'network.json').is_file():return outcome('failed','analysis_execution_failed','Budget calculation did not complete;inspect retained logs')
    try:
        report=json.loads((native/'network.json').read_text(encoding='utf-8'))
        manifest=json.loads((native/'manifest.json').read_text(encoding='utf-8'))
        if report['fluids_version']!='1.3.1' or report['input_sha256']!=digest(paths['project']) or report['geometry_bound'] is not False or not report['calculated_checks'] or report['calculated_checks_pass']!=all(report['calculated_checks'].values()):raise ValueError('Budget source/calculation evidence differs')
        if process.returncode!=(0 if report['calculated_checks_pass'] else 2) or manifest['input_sha256']!=digest(paths['project']) or manifest['input_unchanged'] is not True:raise ValueError('Budget completion/result correspondence differs')
        for name,sha in manifest['artifacts'].items():
            path=(native/name).resolve()
            if not path.is_relative_to(native) or digest(path)!=sha:raise ValueError('Budget artifact evidence differs')
        payload=dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],units=dict(flow='m3/s',pressure='Pa',velocity='m/s'),status='pass' if report['calculated_checks_pass'] else 'fail',
            checks=report['calculated_checks'],supply_flow_m3_s=report['supply_flow_m3_s'],required_source_total_pressure_pa=report['required_source_total_pressure_pa'],
            report=dict(path='analysis/network.json',sha256=digest(native/'network.json')),geometry_bound=False,design_accepted=False)
    except (OSError,ValueError,KeyError) as exc:return outcome('failed','provider_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    try:
        payload=result['payload'];report=json.loads((Path(result_path).parent/payload['report']['path']).read_text(encoding='utf-8'))
        expected='pass' if report['calculated_checks_pass'] else 'fail'
        if payload['status']!=expected or payload['checks']!=report['calculated_checks'] or any(payload[k]!=report[k] for k in ('supply_flow_m3_s','required_source_total_pressure_pa')):raise ValueError('Common air budget differs from retained engine result')
    except (OSError,ValueError,KeyError,TypeError) as exc:raise ValueError('Invalid retained air-budget evidence: '+str(exc)) from exc
