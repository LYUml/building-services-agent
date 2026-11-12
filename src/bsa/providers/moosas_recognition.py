"""Source-checked polygonal spaces from the pinned isolated MOOSAS transform."""
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest
from ..module_contract import read_json,validate
from ..spatial_recognition_check import check

ROOT=Path(__file__).resolve().parents[3]
PIN='dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c'
CAPABILITY='spatial.surface-room-recognition'
PAYLOAD='bsa.spatial-polygons/1'
DESCRIPTION=dict(id='moosas.surface-room-recognition',version='1',license='Apache-2.0',upstream_commit=PIN)
ACCEPTANCE_SCOPE='Declared polygonal room boundary,height and elevation correspondence only;architectural interpretation,thermal/MEP/regulatory readiness and full acceptance remain pending'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'geometry','expectations'}:
        raise ValueError('Surface recognition requires exact geometry/expectations sources')


def projection(request,paths,report):
    expected=read_json(paths['expectations'])
    if set(expected)!={'source_sha256','classification','length_unit','expected','length_tolerance_m','area_tolerance_m2'} or expected['source_sha256']!=digest(paths['geometry']) or expected['length_unit']!='m' or not isinstance(expected['classification'],str) or not expected['classification'].strip():
        raise ValueError('Exact metre source expectations bound to geometry required')
    for room in expected['expected']:
        if set(room)!={'id','boundary_vertices','height_m','floor_elevation_m'}:raise ValueError('Exact source room boundary,height and floor elevation required')
    if report['execution']!='completed' or not report['saved_reload_matches'] or report['point_grid_m']!=1e-9 or report['point_grid_restored'] is not True or report['simulation_executed'] is not False or report['upstream_commit']!=PIN:
        raise ValueError('Completed pinned geometry-only recognition/reload required')
    assessment=check(report['spaces'],expected['expected'],length_tolerance_m=expected['length_tolerance_m'],area_tolerance_m2=expected['area_tolerance_m2'])
    if not assessment['source_geometry_matches']:raise ValueError('Recognized spaces differ from source geometry expectations')
    spaces={r['id']:r for r in report['spaces']};rows=[]
    for row in assessment['rooms']:
        r=spaces[row['matching_ids'][0]]
        rows.append(dict(id=row['source_id'],recognized_id=r['id'],boundary_vertices=r['boundary_vertices'],floor_area_m2=r['area_m2'],height_m=r['height_m'],floor_elevation_m=r['floor_elevation_m']))
    return validate(dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],units=dict(length='m',area='m2'),spaces=rows,point_grid_m=1e-9,source_geometry_matches=True,simulation_ready=False,design_accepted=False))


def execute(request,paths,runtime,out):
    pins={}
    def failed(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    for p in (ROOT/'scripts/probe_moosas_transform.py',ROOT/'scripts/probe_moosas_ifc.py',ROOT/'src/bsa/spatial_recognition_check.py'):
        pins[str(p)]=digest(p)
    if not runtime.get('upstream') or not runtime.get('deps'):return failed('unavailable','runtime_missing','Explicit pinned upstream and isolated dependencies required')
    upstream,deps=(Path(runtime[k]).resolve() for k in ('upstream','deps'))
    if any(not p.is_relative_to(ROOT) or not p.is_dir() for p in (upstream,deps)) or any(not p.is_relative_to(ROOT) for p in paths.values()) or not out.is_relative_to(ROOT):
        return failed('unavailable','runtime_incompatible','Current isolated recognition worker requires repository-local runtime,source and output paths')
    command=[sys.executable,'-X','utf8',str(ROOT/'scripts/probe_moosas_transform.py'),'--source',str(paths['geometry']),'--upstream',str(upstream),'--deps',str(deps),'--out',str(out/'recognition'),'--empty-catalogue','--point-grid-m','1e-9']
    try:
        process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
    except OSError as exc:return failed('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return failed('failed','recognition_timeout',str(exc))
    (out/'stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'stderr.txt').write_text(process.stderr,encoding='utf-8')
    report_path=out/'recognition/probe.json'
    if report_path.is_file():
        report=read_json(report_path);pins.update(report['inputs'])
    if process.returncode!=0:return failed('failed','recognition_failed','Inspect retained isolated recognition logs')
    if not report_path.is_file():return failed('failed','recognition_failed','Worker returned no retained geometry report')
    try:
        if report['inputs'].get(str(paths['geometry']))!=digest(paths['geometry']):raise ValueError('Recognized geometry source identity differs')
        payload=projection(request,paths,report)
    except (ValueError,OSError,KeyError,TypeError) as exc:return failed('failed','recognition_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    request_path=Path(result['request']['path']);request=read_json(request_path)
    paths={k:(request_path.parent/v['path']).resolve() for k,v in request['sources'].items()}
    report=read_json(Path(result_path).parent/'recognition/probe.json')
    if any(result['inputs'].get(p)!=sha for p,sha in report['inputs'].items()):raise ValueError('Recognition source/method pins differ')
    if report['inputs'].get(str(paths['geometry']))!=digest(paths['geometry']):raise ValueError('Recognition input identity differs')
    for name,sha in report['artifacts'].items():
        path=(Path(result_path).parent/'recognition'/name).resolve()
        if not path.is_relative_to(Path(result_path).parent/'recognition') or digest(path)!=sha:raise ValueError('Recognition artifact identity differs')
    if projection(request,paths,report)!=result['payload']:raise ValueError('Spatial polygon payload differs from source check')
