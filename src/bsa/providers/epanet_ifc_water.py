"""Existing saved-native IFC water binding exposed as a common analysis provider."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest
from ..module_contract import read_json
from . import epanet_water

ROOT=epanet_water.ROOT
CAPABILITY='analysis.water.ifc-steady-graph'
PAYLOAD='bsa.bound-water-graph/1'
DESCRIPTION=dict(id='wntr.ifc-steady',version='1',license='BSD-3-Clause AND LGPL-3.0-or-later')
ACCEPTANCE_SCOPE='Saved IFC hollow pipe/profile/port/selected-system agreement and steady water graph only;physical products,junction idealization,K,power,controls,HK and full acceptance remain separate'
METHODS=(*epanet_water.METHODS,'water_binding.py','ifc_drawing.py','circular_geometry.py','circular_elbow.py')


def methods():return [ROOT/'scripts/water_saved_graph.py',Path(epanet_water.__file__),*[ROOT/'src/bsa'/n for n in METHODS]]


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'project','ifc','binding'}:raise ValueError('Bound water requires exact project/ifc/binding sources')


def evidence(request,paths,folder):
    from ..water_binding import derive,reconcile
    binding=read_json(folder/'water-binding.json')
    if binding['inputs']!={str(p):digest(p) for p in paths.values()} or any(binding[k] is not True for k in ('inputs_unchanged','saved_ifc_match','ifc_copy_unchanged')):raise ValueError('Saved water binding evidence differs')
    if digest(folder/'model.ifc')!=digest(paths['ifc']):raise ValueError('Saved water model copy differs')
    for name,sha in binding['artifacts'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or digest(path)!=sha:raise ValueError('Saved water binding artifact differs')
    template=read_json(paths['project']);mapping=read_json(paths['binding'])
    derived,geometry=derive(folder/'model.ifc',template,mapping)
    if derived!=read_json(folder/'network-input.json') or geometry!=read_json(folder/'geometry-binding.json'):raise ValueError('Native water derived geometry differs')
    reconcile(folder/'model.ifc',folder/'network-input.json',template,mapping)
    report,raw=epanet_water.checked_report(folder/'network-input.json',folder/'analysis')
    if binding['calculated_checks_pass']!=report['calculated_checks_pass']:raise ValueError('Native water numerical status differs')
    payload=epanet_water.common(request,report,folder/'analysis')
    payload.update(schema=PAYLOAD,geometry_bound=True)
    for key in ('raw','report'):payload[key]['path']='bound/'+payload[key]['path']
    for key,name in [('network_input','network-input.json'),('binding','water-binding.json'),('model','model.ifc')]:payload[key]=dict(path='bound/'+name,sha256=digest(folder/name))
    payload['model']['format']='IFC4'
    return payload,raw


def execute(request,paths,runtime,out):
    pins={str(p):digest(p) for p in methods()}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if any(importlib.metadata.version(k)!=v for k,v in [('wntr','1.5.0'),('ifcopenshell','0.8.5')]):return outcome('unavailable','runtime_incompatible','Pinned WNTR1.5.0 and IfcOpenShell0.8.5 required')
    except importlib.metadata.PackageNotFoundError:return outcome('unavailable','runtime_missing','Pinned water/native runtime required')
    command=[sys.executable,str(ROOT/'scripts/water_saved_graph.py')]
    for key,path in paths.items():command.extend(['--'+key,str(path)])
    folder=out/'bound';command.extend(['--out',str(folder)])
    try:process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    except OSError as exc:return outcome('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return outcome('failed','provider_timeout',str(exc))
    (out/'provider.stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'provider.stderr.txt').write_text(process.stderr,encoding='utf-8')
    (out/'process.json').write_text(json.dumps(dict(returncode=process.returncode)),encoding='utf-8')
    if process.returncode not in (0,2) or not (folder/'water-binding.json').is_file():return outcome('failed','native_binding_failed','Saved IFC water binding failed;inspect retained logs')
    try:
        report=read_json(folder/'analysis/water.json')
        if report.get('engine_failure'):
            code=report['engine_failure']['kind'];log=(folder/'analysis/worker.log').read_text(encoding='utf-8',errors='replace')
            if code=='application_control_block' and 'application control policy' not in log.lower():raise ValueError('Unsupported policy diagnostic')
            return outcome('failed',code,'Water worker produced no verified hydraulic payload;inspect bound/analysis/worker.log')
        payload,raw=evidence(request,paths,folder)
        if process.returncode!=(0 if payload['status']=='pass' else 2):raise ValueError('Bound water process/status differs')
        library=Path(importlib.metadata.distribution('wntr').locate_file('wntr/epanet/libepanet/windows-x64/epanet22.dll')).resolve()
        if Path(raw['library']).resolve()!=library or digest(library)!=raw['library_sha256']:raise ValueError('Bound native EPANET library differs')
        pins[str(library)]=raw['library_sha256']
    except (OSError,ValueError,KeyError,TypeError) as exc:return outcome('failed','provider_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    try:
        for path in methods():
            if result['inputs'].get(str(path))!=digest(path):raise ValueError('Bound water domain method pin differs')
        request_path=Path(result['request']['path']);request=read_json(request_path)
        paths={k:(request_path.parent/r['path']).resolve() for k,r in request['sources'].items()}
        folder=Path(result_path).parent;payload,raw=evidence(request,paths,folder/'bound')
        library=Path(importlib.metadata.distribution('wntr').locate_file('wntr/epanet/libepanet/windows-x64/epanet22.dll')).resolve()
        if Path(raw['library']).resolve()!=library or result['inputs'].get(str(library))!=raw['library_sha256']:raise ValueError('Bound native library pin differs')
        if payload!=result['payload'] or read_json(folder/'process.json')['returncode']!=(0 if payload['status']=='pass' else 2):raise ValueError('Common bound water evidence differs')
    except (OSError,ValueError,KeyError,TypeError) as exc:raise ValueError('Invalid retained bound-water evidence: '+str(exc)) from exc
