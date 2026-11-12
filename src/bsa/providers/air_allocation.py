"""Thin common boundary around the existing classified airflow allocation engine."""
import importlib.metadata
import json
from pathlib import Path
from ..cli import digest
from ..module_contract import read_json, validate
from ..workspace import allowed

ROOT = Path(__file__).resolve().parents[3]
CAPABILITY = 'analysis.air.classified-allocation'
PAYLOAD = 'bsa.air-allocation/1'
DESCRIPTION = dict(id='bsa.classified-air-allocation', version='1', license='NOASSERTION')
ACCEPTANCE_SCOPE = 'Conditional thermal balance and nearest-centre allocation only; room loads, ADPI, routing, native geometry and regulatory acceptance remain pending'


def validate_request(request):
    if request['capability'] != CAPABILITY or set(request['sources']) != {'project'}:
        raise ValueError('Air allocation requires exact project source')


def sources(project_path):
    from ..air_allocation import reference_files
    project = read_json(project_path)
    relative = project['boundary']
    if not isinstance(relative, str) or not relative.strip() or Path(relative).is_absolute():
        raise ValueError('Relative allocation boundary required')
    boundary = (project_path.parent/relative).resolve()
    refs = reference_files(project_path, project)
    if not allowed(boundary) or any(not allowed(p) for p in refs):
        raise ValueError('Allocation source outside selected workspace')
    if digest(boundary) != project['boundary_sha256']:
        raise ValueError('Allocation boundary hash differs')
    return project, boundary, {str(boundary): digest(boundary), **{str(p): h for p, h in refs.items()}}


def methods():
    return {str(ROOT/'src/bsa'/name): digest(ROOT/'src/bsa'/name)
            for name in ('air_allocation.py', 'air_load.py', 'service_areas.py')}


def common(request, report, folder):
    load = report['load']
    return validate(dict(schema=PAYLOAD, coordinate_frame=request['coordinate_frame'],
        units=dict(power='kW thermal', flow='L/s', area='m2', length='m'),
        terminals=[{k: row[k] for k in ('id', 'maximum_flow_L_s', 'minimum_flow_L_s', 'allocated_load_area_m2')}
                   for row in report['terminals']],
        **{k: load[k] for k in ('total_cooling_kW_thermal', 'sensible_trial_kW_thermal', 'supply_flow_L_s')},
        turndown=report['turndown'], report=dict(path='analysis/allocation.json', sha256=digest(folder/'allocation.json')),
        geometry_bound=False, room_sensible_load_verified=False, design_accepted=False))


def execute(request, paths, runtime, out):
    from ..air_allocation import run
    pins = methods()
    try:
        try:
            version = importlib.metadata.version('shapely')
        except importlib.metadata.PackageNotFoundError:
            return dict(status='unavailable', diagnostics=[dict(code='runtime_missing', message='Pinned Shapely2.2.0 not installed')], payload=None, pins=pins)
        if version != '2.2.0':
            return dict(status='unavailable', diagnostics=[dict(code='runtime_incompatible', message='Pinned Shapely2.2.0 required')], payload=None, pins=pins)
        _, _, discovered = sources(paths['project'])
        pins.update(discovered)
        report = run(paths['project'], out/'analysis')
        payload = common(request, report, out/'analysis')
    except (ValueError, OSError, KeyError) as exc:
        return dict(status='failed', diagnostics=[dict(code='air_allocation_failed', message=str(exc))], payload=None, pins=pins)
    return dict(status='completed', diagnostics=[], payload=payload, pins=pins)


def verify_evidence(result, result_path):
    if result['execution']['status'] != 'completed':
        return
    from ..air_allocation import prepare
    request_path = Path(result['request']['path'])
    request = read_json(request_path)
    project_path = (request_path.parent/request['sources']['project']['path']).resolve()
    project, boundary, pins = sources(project_path)
    pins.update(methods())
    pins[str(project_path)] = digest(project_path)
    if any(result['inputs'].get(p) != sha for p, sha in pins.items()):
        raise ValueError('Allocation source/method evidence differs')
    expected = prepare(read_json(boundary), project['terminals'], project['load_inputs'], project['turndown'])
    expected.update(inputs={str(project_path): digest(project_path), str(boundary): digest(boundary)}, geometry_basis=project['geometry_basis'])
    expected['inputs'].update({p: sha for p, sha in pins.items() if p not in methods() and p != str(project_path)})
    folder = Path(result_path).parent/'analysis'
    report = read_json(folder/'allocation.json')
    if report != json.loads(json.dumps(expected)):
        raise ValueError('Allocation retained result differs from source replay')
    if common(request, report, folder) != result['payload']:
        raise ValueError('Common allocation payload differs from source replay')
