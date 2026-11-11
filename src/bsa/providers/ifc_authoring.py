"""Thin isolated provider for the existing native IfcOpenShell BIM authoring engine."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='authoring.ifc.bim'
PAYLOAD='bsa.model-artifact/1'
DESCRIPTION=dict(id='ifcopenshell.bim-authoring',version='0.8.5',license='LGPL-3.0-or-later')
ACCEPTANCE_SCOPE='Scoped native IFC authoring/reopening checks only;visual,product,coordination,analysis,regulatory and full design acceptance remain separate'


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'project'}:raise ValueError('BIM authoring requires exact project source and supported capability')


def execute(request,paths,runtime,out):
    names=('bim.py','cli.py','engine.py','circular_geometry.py','circular_elbow.py','rectangular_geometry.py','rectangular_elbow.py')
    pins={str(ROOT/'src/bsa'/name):digest(ROOT/'src/bsa'/name) for name in names}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    try:
        if importlib.metadata.version('ifcopenshell')!='0.8.5':return outcome('unavailable','runtime_incompatible','Pinned IfcOpenShell0.8.5 required')
    except importlib.metadata.PackageNotFoundError:return outcome('unavailable','runtime_missing','IfcOpenShell0.8.5 is not installed')
    native=out/'native'
    try:process=subprocess.run([sys.executable,'-m','bsa.bim',str(paths['project']),'--out',str(native)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    except OSError as exc:return outcome('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return outcome('failed','provider_timeout',str(exc))
    (out/'provider.stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'provider.stderr.txt').write_text(process.stderr,encoding='utf-8')
    (out/'process.json').write_text(json.dumps(dict(returncode=process.returncode)),encoding='utf-8')
    if process.returncode!=0:return outcome('failed','native_authoring_failed','Native authoring did not complete;inspect retained logs')
    try:
        report=json.loads((native/'bim-verification.json').read_text(encoding='utf-8'))
        if report['ifcopenshell_version']!='0.8.5' or report['input_sha256']!=digest(paths['project']) or report['ifc_sha256']!=digest(native/'model.ifc') or report['model_checks_pass'] is not True or not report['checks'] or not all(v is True for v in report['checks'].values()):raise ValueError('Native authoring source/reopen checks differ')
        payload=dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],length_unit='m',model=dict(path='native/model.ifc',sha256=digest(native/'model.ifc'),format='IFC4'),
            verification=dict(path='native/bim-verification.json',sha256=digest(native/'bim-verification.json')),geometry_scope=report['geometry_scope'],checks=report['checks'],design_accepted=False)
    except (OSError,ValueError,KeyError) as exc:return outcome('failed','provider_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)
