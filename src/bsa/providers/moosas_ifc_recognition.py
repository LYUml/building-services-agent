"""Compose saved-native IFC intake and the existing isolated MOOSAS recognizer."""
import json
import math
from pathlib import Path
from ..cli import digest
from ..module_contract import read_json
from .moosas_recognition import PIN,PAYLOAD,ACCEPTANCE_SCOPE

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='spatial.ifc-room-recognition'
DESCRIPTION=dict(id='moosas.ifc-room-recognition',version='1',license='Apache-2.0',upstream_commit=PIN)


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'ifc','settings'}:
        raise ValueError('Native room recognition requires exact ifc/settings sources')


def settings(path):
    values=read_json(path)
    if not isinstance(values,dict) or set(values)!={'length_tolerance_m','area_tolerance_m2'} or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values.values()):
        raise ValueError('Exact explicit positive source length/area tolerances required')
    return values


def execute(request,paths,runtime,out):
    from ..modules import run as module
    from ..ifc_space_surfaces import run as intake
    pins={str(ROOT/'src/bsa'/p):digest(ROOT/'src/bsa'/p) for p in ('ifc_space_surfaces.py','solid_clash.py','spatial_recognition_check.py','providers/moosas_recognition.py')}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:values=settings(paths['settings'])
    except (ValueError,OSError,KeyError) as exc:return outcome('failed','invalid_source_settings',str(exc))
    if not runtime.get('upstream') or not runtime.get('deps'):return outcome('unavailable','runtime_missing','Explicit pinned MOOSAS upstream/dependencies required')
    if not out.is_relative_to(ROOT) or any(not p.is_relative_to(ROOT) for p in paths.values()):
        return outcome('unavailable','runtime_incompatible','Current recognition worker requires repository-local source/output paths')
    try:
        intake(paths['ifc'],out/'intake',**values)
        nested=out/'intake/request.json';data=read_json(nested)
        for key in ('project_id','scenario_id','coordinate_frame'):data[key]=request[key]
        nested.write_text(json.dumps(data,indent=2),encoding='utf-8')
        result=module(nested,'moosas.surface-room-recognition',out/'recognition',runtime=runtime)
        pins.update(result['inputs'])
        if result['execution']['status']!='completed':return dict(status=result['execution']['status'],diagnostics=result['execution']['diagnostics'],payload=None,pins=pins)
    except ImportError as exc:return outcome('unavailable','native_source_runtime_unavailable',str(exc))
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:return outcome('failed','native_recognition_failed',str(exc))
    return dict(status='completed',diagnostics=[],payload=result['payload'],pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    from ..modules import verify_result
    request_path=Path(result['request']['path']);request=read_json(request_path)
    paths={k:(request_path.parent/v['path']).resolve() for k,v in request['sources'].items()}
    root=Path(result_path).parent;nested=verify_result(root/'recognition/result.json')
    generated=root/'intake/request.json';data=read_json(generated)
    if Path(nested['request']['path']).resolve()!=generated.resolve() or nested['provider']['id']!='moosas.surface-room-recognition' or nested['execution']['status']!='completed':raise ValueError('Nested native recognition identity differs')
    if any(data[k]!=request[k] for k in ('project_id','scenario_id','coordinate_frame')):raise ValueError('Nested source recognition frame/project differs')
    if (generated.parent/data['sources']['ifc_source']['path']).resolve()!=paths['ifc']:raise ValueError('Nested recognition replaced original IFC')
    if any(result['inputs'].get(p)!=sha for p,sha in nested['inputs'].items()):raise ValueError('Native recognition source/method evidence differs')
    expectation=read_json(generated.parent/data['sources']['expectations']['path'])
    if any(expectation[k]!=v for k,v in settings(paths['settings']).items()):raise ValueError('Native recognition changed source tolerances')
    if result['payload']!=nested['payload']:raise ValueError('Common native recognition payload differs from verified nested result')
