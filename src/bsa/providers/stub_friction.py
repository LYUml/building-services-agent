"""Common analysis boundary around the existing native short-stub friction component."""
import importlib.metadata
from pathlib import Path
from ..cli import digest
from ..module_contract import read_json,validate

CAPABILITY='analysis.air.native-stub-friction'
PAYLOAD='bsa.straight-friction-components/1'
DESCRIPTION=dict(id='fluids.native-stub-friction',version='1.3.1',license='MIT')
ACCEPTANCE_SCOPE='Native-source fully-developed straight-friction component only;short-duct development,joints,air state,whole pressure,fan and complete engineering acceptance remain pending'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'stubs','basis'}:raise ValueError('Native friction requires exact verified stub report and property basis')


def common(request,report,folder):
    calculation=report['calculation']
    if calculation['coordinate_frame']!=request['coordinate_frame']:raise ValueError('Native friction source and requested frame differ')
    complete=calculation['status']=='calculated'
    return validate(dict(schema=PAYLOAD,coordinate_frame=calculation['coordinate_frame'],units=dict(flow='L/s',flow_si='m3/s',length='m',pressure='Pa',velocity='m/s',density='kg/m3',dynamic_viscosity='Pa.s',dimensionless='1'),
        status='pass' if complete else 'pending',checks=dict(case_domain_complete=complete),components=calculation['terminals'],case_count=2*len(calculation['terminals']),fluid_basis=calculation['basis'],
        report=dict(path='analysis/straight-friction.json',sha256=digest(folder/'straight-friction.json')),geometry_bound=True,engineering_status='pending',fully_developed_flow_verified=False,whole_system_pressure_complete=False,design_accepted=False))


def execute(request,paths,runtime,out):
    pins={}
    def failed(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if importlib.metadata.version('fluids')!='1.3.1':return failed('unavailable','runtime_incompatible','Pinned fluids1.3.1 required')
    except importlib.metadata.PackageNotFoundError:return failed('unavailable','runtime_missing','Pinned fluids1.3.1 not installed')
    try:
        from .. import spatial_stub_friction as engine
        pins[str(Path(engine.__file__).resolve())]=digest(Path(engine.__file__))
        report=engine.run(paths['stubs'],paths['basis'],out/'analysis');pins.update(report['inputs']);payload=common(request,report,out/'analysis')
    except (OSError,ValueError,KeyError,TypeError,ImportError) as exc:return failed('failed','native_friction_analysis_failed',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['acceptance']!=dict(status='pending',scope=ACCEPTANCE_SCOPE):raise ValueError('Friction engineering acceptance must remain pending')
    if result['execution']['status']!='completed':return
    from .. import spatial_stub_friction as engine
    request_path=Path(result['request']['path']);request=read_json(request_path);sources={role:(request_path.parent/row['path']).resolve() for role,row in request['sources'].items()}
    folder=Path(result_path).parent/'analysis';report=engine.verify(folder)
    if Path(report['stubs'])!=sources['stubs'] or Path(report['basis'])!=sources['basis']:raise ValueError('Friction report replaced declared source/basis')
    if any(result['inputs'].get(p)!=sha for p,sha in report['inputs'].items()):raise ValueError('Common friction omitted native source/method evidence')
    if common(request,report,folder)!=result['payload']:raise ValueError('Common friction projection differs from native replay')
