"""Thin common boundary around the existing conditional single-phase calculator."""
import importlib.metadata
from pathlib import Path
from ..cli import digest
from ..module_contract import read_json,validate

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='analysis.electrical.single-phase-circuits'
PAYLOAD='bsa.electrical-circuits/1'
DESCRIPTION=dict(id='bsa.single-phase-circuits',version='1',license='NOASSERTION')
ACCEPTANCE_SCOPE='Declared single-phase circuit current,ampacity and voltage-drop checks only;fault/protection,native geometry,code applicability and full engineering acceptance remain pending'


class UnsupportedElectricalSemantics(ValueError):
    pass


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'project'}:raise ValueError('Electrical provider requires exact project source')


def validate_project(project):
    """This declared single-phase boundary must not ignore other load semantics."""
    from ..engine import validate as validate_legacy
    validate_legacy(project)
    fields={'name','supply_voltage_v','sources','circuits','devices'}
    circuit={'id','phase','demand_factor','breaker_a','tabulated_ampacity_a','correction_factor','route_length_m','vd_mv_a_m','max_vd_percent','source'}
    device={'id','circuit','electrical_kw','power_factor','x_m','y_m','source'}
    if set(project)!=fields:raise UnsupportedElectricalSemantics('Unsupported electrical project fields;explicit single-phase schema required')
    for kind,allowed in (('circuits',circuit),('devices',device)):
        for row in project[kind]:
            if set(row)!=allowed:raise UnsupportedElectricalSemantics('Unsupported '+kind+' fields for '+row['id']+';three-phase,thermal or other semantics require a separate supported adapter')
    return project


def common(request,project,report,folder):
    checks={k:all(c['checks'][k] for c in report['circuits']) for k in ('ib_le_in','in_le_iz','voltage_drop')}
    return validate(dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],
        units=dict(real_power='kW electrical',apparent_power='VA',current='A',voltage='V',length='m'),
        status='pass' if report['calculated_checks_pass'] else 'fail',checks=checks,supply_voltage_v=project['supply_voltage_v'],
        circuits=report['circuits'],phase_demand_va=report['phase_demand_va'],pending=report['pending'],
        report=dict(path='analysis/calculations.json',sha256=digest(folder/'calculations.json')),geometry_bound=False,design_accepted=False))


def execute(request,paths,runtime,out):
    from ..cli import run
    pins={str(ROOT/'src/bsa'/n):digest(ROOT/'src/bsa'/n) for n in ('engine.py','cli.py')}
    def failed(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if importlib.metadata.version('ezdxf')!='1.4.5':return failed('unavailable','runtime_incompatible','Pinned ezdxf1.4.5 required')
    except importlib.metadata.PackageNotFoundError:return failed('unavailable','runtime_missing','Pinned ezdxf1.4.5 not installed')
    try:
        project=validate_project(read_json(paths['project']));report=run(paths['project'],out/'analysis');payload=common(request,project,report,out/'analysis')
    except UnsupportedElectricalSemantics as exc:return failed('failed','unsupported_source_semantics',str(exc))
    except (ValueError,OSError,KeyError) as exc:return failed('failed','electrical_analysis_failed',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    from ..engine import calculate
    request_path=Path(result['request']['path']);request=read_json(request_path)
    project_path=(request_path.parent/request['sources']['project']['path']).resolve();project=validate_project(read_json(project_path))
    folder=Path(result_path).parent/'analysis';report=read_json(folder/'calculations.json')
    for name in ('engine.py','cli.py'):
        path=ROOT/'src/bsa'/name
        if result['inputs'].get(str(path))!=digest(path):raise ValueError('Electrical method evidence differs')
    if report!=calculate(project):raise ValueError('Electrical retained result differs from source replay')
    if common(request,project,report,folder)!=result['payload']:raise ValueError('Common electrical payload differs from source replay')
