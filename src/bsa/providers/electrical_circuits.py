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
        report=dict(path='analysis/calculations.json',sha256=digest(folder/'calculations.json')),
        schematic_dxf=dict(path='analysis/devices.dxf',sha256=digest(folder/'devices.dxf'),format='DXF'),geometry_bound=False,design_accepted=False))


def verify_schematic(project,path):
    """Read saved entities against explicit source IDs/coordinates and legacy style."""
    import ezdxf
    doc=ezdxf.readfile(path);entities=list(doc.modelspace())
    if doc.units!=6 or len(entities)!=2*len(project['devices']) or any(e.dxftype() not in ('CIRCLE','TEXT') for e in entities):raise ValueError('Electrical source schematic units/entity inventory differs')
    def xyz(point):return tuple(round(float(v),9) for v in point)
    circles=sorted((e.dxf.layer,xyz(e.dxf.center),round(e.dxf.radius,9)) for e in entities if e.dxftype()=='CIRCLE')
    texts=sorted((e.dxf.layer,xyz(e.dxf.insert),e.dxf.text) for e in entities if e.dxftype()=='TEXT')
    expected_c=sorted(('BSA_DEVICES',(round(d['x_m'],9),round(d['y_m'],9),0.),.12) for d in project['devices'])
    expected_t=sorted(('BSA_LABELS',(round(d['x_m']+.2,9),round(d['y_m'],9),0.),d['id']+' / '+d['circuit']) for d in project['devices'])
    if circles!=expected_c or texts!=expected_t:raise ValueError('Electrical source schematic IDs/coordinates differ')
    for e in entities:
        if e.dxf.get('invisible',0) or xyz(e.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):raise ValueError('Electrical schematic hidden or nonplanar entity')
        if e.dxftype()=='TEXT' and (abs(e.dxf.height-.12)>1e-9 or e.dxf.get('rotation',0)!=0 or e.dxf.get('width',1)!=1 or e.dxf.get('text_generation_flag',0)!=0 or e.dxf.get('oblique',0)!=0 or e.dxf.get('halign',0)!=0 or e.dxf.get('valign',0)!=0):raise ValueError('Electrical schematic label style differs')
    for name in ('BSA_DEVICES','BSA_LABELS'):
        layer=doc.layers.get(name)
        if layer.is_off() or layer.is_frozen():raise ValueError('Electrical schematic layer hidden')
    positions={}
    for d in project['devices']:positions.setdefault((round(d['x_m'],9),round(d['y_m'],9)),[]).append(d['id'])
    return dict(device_count=len(project['devices']),source_ids_coordinates_match=True,symbolic_style_checked=True,
        coincident_symbol_ids=[ids for ids in positions.values() if len(ids)>1],geometry_bound=False)


def execute(request,paths,runtime,out):
    from ..cli import run
    pins={str(ROOT/'src/bsa'/n):digest(ROOT/'src/bsa'/n) for n in ('engine.py','cli.py')}
    def failed(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if importlib.metadata.version('ezdxf')!='1.4.5':return failed('unavailable','runtime_incompatible','Pinned ezdxf1.4.5 required')
    except importlib.metadata.PackageNotFoundError:return failed('unavailable','runtime_missing','Pinned ezdxf1.4.5 not installed')
    try:
        project=validate_project(read_json(paths['project']));report=run(paths['project'],out/'analysis');verify_schematic(project,out/'analysis/devices.dxf');payload=common(request,project,report,out/'analysis')
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
    verify_schematic(project,folder/'devices.dxf')
    if common(request,project,report,folder)!=result['payload']:raise ValueError('Common electrical payload differs from source replay')
