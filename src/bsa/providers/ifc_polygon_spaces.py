"""Native IFC polygon-space provider with no MOOSAS transform/runtime dependency."""
import json
from pathlib import Path
from ..cli import digest
from ..module_contract import read_json,validate

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='spatial.ifc-room-recognition'
PAYLOAD='bsa.spatial-polygons/1'
DESCRIPTION=dict(id='ifcopenshell.polygon-spaces',version='0.8.5',license='LGPL-3.0-or-later')
ACCEPTANCE_SCOPE='Saved IFC vertical polygon-space body correspondence only;architectural interpretation,thermal/MEP/regulatory readiness and full acceptance remain pending'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'ifc','settings'}:
        raise ValueError('Native polygon spaces require exact ifc/settings sources')


def calculate(request,paths):
    from ..ifc_space_surfaces import prepare,read_settings
    _,declaration,audit=prepare(paths['ifc'],**read_settings(paths['settings']))
    metadata={s['guid']:s for s in audit['spaces']}
    payload=validate(dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],units=dict(length='m',area='m2'),
        spaces=[dict(id=r['id'],recognized_id=r['id'],boundary_vertices=r['boundary_vertices'],floor_area_m2=metadata[r['id']]['floor_area_m2'],height_m=r['height_m'],floor_elevation_m=r['floor_elevation_m']) for r in declaration['expected']],
        point_grid_m=None,source_geometry_matches=True,simulation_ready=False,design_accepted=False))
    return dict(native_audit=audit,payload=payload)


def execute(request,paths,runtime,out):
    pins={str(ROOT/'src/bsa'/p):digest(ROOT/'src/bsa'/p) for p in ('ifc_space_surfaces.py','solid_clash.py')}
    try:report=calculate(request,paths)
    except ImportError as exc:return dict(status='unavailable',diagnostics=[dict(code='native_runtime_unavailable',message=str(exc))],payload=None,pins=pins)
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:return dict(status='failed',diagnostics=[dict(code='native_polygon_space_failed',message=str(exc))],payload=None,pins=pins)
    (out/'native-space-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return dict(status='completed',diagnostics=[],payload=report['payload'],pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    request_path=Path(result['request']['path']);request=read_json(request_path)
    paths={k:(request_path.parent/v['path']).resolve() for k,v in request['sources'].items()}
    report=read_json(Path(result_path).parent/'native-space-audit.json')
    expected=calculate(request,paths)
    if expected!=report or report['payload']!=result['payload']:raise ValueError('Native polygon space evidence differs from saved-source replay')
    for name in ('ifc_space_surfaces.py','solid_clash.py'):
        p=ROOT/'src/bsa'/name
        if result['inputs'].get(str(p))!=digest(p):raise ValueError('Native polygon method evidence differs')
