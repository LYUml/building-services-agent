"""Typed boundary around the existing WNTR/EPANET worker; no new solver."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest
from ..module_contract import read_json

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='analysis.water.steady-graph'
PAYLOAD='bsa.water-graph/1'
DESCRIPTION=dict(id='wntr.epanet-steady',version='1.5.0',license='BSD-3-Clause')
ACCEPTANCE_SCOPE='Declared steady water/circulation graph only;native routing,fluid/demand/curve applicability,products,power,controls and jurisdiction/full design acceptance remain separate'
METHODS=('epanet.py','epanet_energy.py','engine.py','cli.py')


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'project'}:raise ValueError('Steady water analysis requires exact project source and supported capability')


def common(request,report,folder):
    return dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],
        units=dict(flow='m3/s',head='m',velocity='m/s'),pressure_basis='static pressure head in metres of water',
        status='pass' if report['calculated_checks_pass'] else 'fail',checks=report['checks'],
        junctions=[{k:r[k] for k in ('id','head_m','static_pressure_head_m','delivered_m3_s','design_demand_m3_s')} for r in report['junctions']],
        pipes=[{k:r[k] for k in ('id','flow_m3_s','velocity_m_s')} for r in report['pipes']],
        pumps=[{k:r[k] for k in ('id','flow_m3_s','head_gain_m')} for r in report['pumps']],
        report=dict(path='analysis/water.json',sha256=digest(folder/'water.json')),
        raw=dict(path='analysis/raw.json',sha256=digest(folder/'raw.json')),
        geometry_bound=False,design_accepted=False)


def checked_report(source,folder):
    from ..epanet import validate,evaluate
    report=read_json(folder/'water.json');raw=read_json(folder/'raw.json');project=validate(read_json(source))
    if digest(folder/'source-copy.json')!=digest(source):raise ValueError('Water worker source copy differs')
    if report.get('engine_error') or report.get('engine_failure') or report['input_sha256']!=digest(source) or report['input_unchanged'] is not True or report['source_data']!=project or report['design_accepted'] is not False:raise ValueError('Water input/completion evidence differs')
    if raw['versions']['wntr']!='1.5.0' or raw['engine_version']!=20200:raise ValueError('Pinned WNTR1.5.0/EPANET2.2 evidence required')
    for name,sha in report['artifacts'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or digest(path)!=sha:raise ValueError('Water domain artifact evidence differs')
    expected=evaluate(project,raw)
    if any(report.get(k)!=v for k,v in expected.items()):raise ValueError('Water result differs from source/raw numerical replay')
    if report['runtime']!={k:raw[k] for k in report['runtime']}:raise ValueError('Water runtime evidence differs')
    return report,raw


def execute(request,paths,runtime,out):
    pins={str(ROOT/'src/bsa'/n):digest(ROOT/'src/bsa'/n) for n in METHODS}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if importlib.metadata.version('wntr')!='1.5.0':return outcome('unavailable','runtime_incompatible','Pinned WNTR1.5.0 required')
    except importlib.metadata.PackageNotFoundError:return outcome('unavailable','runtime_missing','WNTR1.5.0 is not installed')
    native=out/'analysis'
    try:process=subprocess.run([sys.executable,'-m','bsa.epanet',str(paths['project']),'--out',str(native)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    except OSError as exc:return outcome('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return outcome('failed','provider_timeout',str(exc))
    (out/'provider.stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'provider.stderr.txt').write_text(process.stderr,encoding='utf-8')
    (out/'process.json').write_text(json.dumps(dict(returncode=process.returncode)),encoding='utf-8')
    if process.returncode not in (0,2) or not (native/'water.json').is_file():return outcome('failed','analysis_execution_failed','Water calculation did not complete;inspect retained logs')
    try:
        saved=read_json(native/'water.json')
        if saved.get('engine_failure'):
            failure=saved['engine_failure'];log=(native/'worker.log').read_text(encoding='utf-8',errors='replace')
            code=failure['kind']
            if code=='application_control_block' and 'application control policy' not in log.lower():raise ValueError('Unsupported policy-block diagnostic')
            return outcome('failed',code,'Water worker did not produce verified hydraulic results;inspect analysis/worker.log')
        report,raw=checked_report(paths['project'],native)
        if process.returncode!=(0 if report['calculated_checks_pass'] else 2):raise ValueError('Water process/result status differs')
        library=Path(importlib.metadata.distribution('wntr').locate_file('wntr/epanet/libepanet/windows-x64/epanet22.dll')).resolve()
        if Path(raw['library']).resolve()!=library or digest(library)!=raw['library_sha256']:raise ValueError('Selected native EPANET library differs')
        pins[str(library)]=raw['library_sha256']
        payload=common(request,report,native)
    except (OSError,ValueError,KeyError,TypeError) as exc:return outcome('failed','provider_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    try:
        for name in METHODS:
            path=ROOT/'src/bsa'/name
            if result['inputs'].get(str(path))!=digest(path):raise ValueError('Water domain method pin missing or changed')
        request_path=Path(result['request']['path']);request=read_json(request_path)
        source=(request_path.parent/request['sources']['project']['path']).resolve()
        folder=Path(result_path).parent/'analysis';report,raw=checked_report(source,folder)
        library=Path(importlib.metadata.distribution('wntr').locate_file('wntr/epanet/libepanet/windows-x64/epanet22.dll')).resolve()
        if Path(raw['library']).resolve()!=library or result['inputs'].get(str(library))!=raw['library_sha256']:raise ValueError('Water native library pin differs')
        if result['payload']!=common(request,report,folder):raise ValueError('Common water graph differs from retained engine result')
        process=read_json(Path(result_path).parent/'process.json')
        if process['returncode']!=(0 if report['calculated_checks_pass'] else 2):raise ValueError('Water completion status differs')
    except (OSError,ValueError,KeyError,TypeError) as exc:raise ValueError('Invalid retained water-graph evidence: '+str(exc)) from exc
