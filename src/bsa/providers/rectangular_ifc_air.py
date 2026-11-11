"""Thin saved-IFC budget provider using existing geometry binding and fluids."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest
from ..module_contract import read_json
from .rectangular_air import verify_evidence as verify_numerical

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='analysis.air.rectangular-ifc-tree'
PAYLOAD='bsa.bound-air-budget/1'
DESCRIPTION=dict(id='fluids.rectangular-ifc-budget',version='1',license='MIT AND LGPL-3.0-or-later')
ACCEPTANCE_SCOPE='Saved IFC/source rectangular route agreement and prescribed air budget only;K,method applicability,junction physics,products,fan selection and full engineering acceptance remain separate'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'project','model','binding','ifc'}:raise ValueError('Saved rectangular budget requires exact project/model/binding/ifc sources')


def execute(request,paths,runtime,out):
    script=ROOT/'scripts/rectangular_saved_budget.py'
    names=('rectangular_binding.py','network_binding.py','rectangular_network.py','network.py','bim.py','rectangular_geometry.py','rectangular_elbow.py','circular_geometry.py','circular_elbow.py','cli.py','engine.py')
    pins={str(p):digest(p) for p in [script,ROOT/'src/bsa/providers/rectangular_air.py',*[ROOT/'src/bsa'/n for n in names]]}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if any(importlib.metadata.version(k)!=v for k,v in [('fluids','1.3.1'),('ifcopenshell','0.8.5')]):return outcome('unavailable','runtime_incompatible','Pinned fluids1.3.1 and IfcOpenShell0.8.5 required')
    except importlib.metadata.PackageNotFoundError:return outcome('unavailable','runtime_missing','Pinned fluids and native IFC runtime required')
    bound=out/'bound';command=[sys.executable,str(script)]
    for key,path in paths.items():command.extend(['--'+key,str(path)])
    command.extend(['--out',str(bound)])
    try:process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    except OSError as exc:return outcome('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return outcome('failed','provider_timeout',str(exc))
    (out/'provider.stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'provider.stderr.txt').write_text(process.stderr,encoding='utf-8')
    (out/'process.json').write_text(json.dumps(dict(returncode=process.returncode)),encoding='utf-8')
    if process.returncode not in (0,2) or not (bound/'network-binding.json').is_file():return outcome('failed','native_binding_failed','Saved native reconciliation/budget did not complete;inspect retained logs')
    try:
        report=read_json(bound/'analysis/network.json');binding=read_json(bound/'network-binding.json')
        if binding['inputs']!={str(p):digest(p) for p in paths.values()} or binding['saved_ifc_geometry_match'] is not True or binding['complete_source_duct_coverage'] is not True or report['fluids_version']!='1.3.1':raise ValueError('Saved native binding evidence differs')
        if report['input_sha256']!=digest(bound/'network-input.json') or binding['calculated_checks_pass']!=report['calculated_checks_pass']:raise ValueError('Derived input/result binding differs')
        if process.returncode!=(0 if report['calculated_checks_pass'] else 2):raise ValueError('Budget return code differs')
        payload=dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],units=dict(flow='m3/s',pressure='Pa',velocity='m/s'),status='pass' if report['calculated_checks_pass'] else 'fail',checks=report['calculated_checks'],supply_flow_m3_s=report['supply_flow_m3_s'],required_source_total_pressure_pa=report['required_source_total_pressure_pa'],geometry_bound=True,design_accepted=False,
            network_input=dict(path='bound/network-input.json',sha256=digest(bound/'network-input.json')),report=dict(path='bound/analysis/network.json',sha256=digest(bound/'analysis/network.json')),binding=dict(path='bound/network-binding.json',sha256=digest(bound/'network-binding.json')),model=dict(path='bound/verified-model.ifc',sha256=digest(bound/'verified-model.ifc'),format='IFC4'))
    except (OSError,ValueError,KeyError) as exc:return outcome('failed','provider_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    verify_numerical(result,result_path)
    try:
        folder=Path(result_path).parent;request_path=Path(result['request']['path']);request=read_json(request_path)
        paths={k:(request_path.parent/r['path']).resolve() for k,r in request['sources'].items()}
        payload=result['payload'];binding=read_json(folder/payload['binding']['path'])
        if binding['inputs']!={str(p):digest(p) for p in paths.values()} or binding['saved_ifc_geometry_match'] is not True or binding['complete_source_duct_coverage'] is not True or payload['model']['sha256']!=digest(paths['ifc']):raise ValueError('Bound source/model correspondence differs')
        from ..network_binding import _prepare
        from ..rectangular_binding import inspect_saved
        model=read_json(paths['model']);mapping=read_json(paths['binding']);derived,_=_prepare(read_json(paths['project']),model,mapping,rectangular=True)
        if 'network_input' not in payload:raise ValueError('Explicit derived network artifact required')
        generated=folder/payload['network_input']['path']
        if read_json(generated)!=derived:raise ValueError('Derived geometry changed')
        report=read_json(folder/payload['report']['path'])
        if report['input_sha256']!=digest(generated) or binding['calculated_checks_pass']!=report['calculated_checks_pass']:raise ValueError('Derived input/result binding differs')
        inspect_saved(folder/payload['model']['path'],model,generated,mapping)
    except (OSError,ValueError,KeyError,TypeError) as exc:raise ValueError('Invalid saved-IFC budget evidence: '+str(exc)) from exc
