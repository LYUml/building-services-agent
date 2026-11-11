"""Native IFC provider for the common box-space contract;no MOOSAS runtime needed."""
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest

ROOT=Path(__file__).resolve().parents[3]
CAPABILITY='spatial.ifc-boxes.exchange'
PAYLOAD='bsa.spatial-boxes/1'
DESCRIPTION=dict(id='ifcopenshell.box-spaces',version='0.8.5',license='LGPL-3.0-or-later')


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'ifc','binding'}:raise ValueError('IFC box provider requires exact ifc/binding sources')


def execute(request,paths,runtime,out):
    script=ROOT/'scripts/ifc_box_exchange.py'
    methods=[script,ROOT/'scripts/moosas_space_exchange.py',ROOT/'scripts/probe_moosas_ifc.py',
        *(ROOT/'src/bsa'/name for name in ('thermal_binding.py','thermal_geometry.py','annual_energy.py','box_geometry.py'))]
    pins={str(p):digest(p) for p in methods}
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    frame=out/'coordinate-frame.json';frame.write_text(json.dumps(request['coordinate_frame']),encoding='utf-8')
    report=out/'native-exchange.json'
    command=[sys.executable,str(script),'--ifc',str(paths['ifc']),'--binding',str(paths['binding']),'--frame',str(frame),'--out',str(report)]
    try:process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    except OSError as exc:return outcome('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return outcome('failed','provider_timeout',str(exc))
    (out/'provider.stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'provider.stderr.txt').write_text(process.stderr,encoding='utf-8')
    (out/'process.json').write_text(json.dumps(dict(returncode=process.returncode)),encoding='utf-8')
    if process.returncode!=0:return outcome('failed','native_exchange_failed','Native IFC exchange failed;inspect retained provider logs')
    try:
        result=json.loads(report.read_text(encoding='utf-8'))
        if result['geometry']['ifc_sha256']!=digest(paths['ifc']) or result['geometry']['complete_space_coverage'] is not True:raise ValueError('Native source coverage differs')
        payload=result['payload']
    except (OSError,ValueError,KeyError) as exc:return outcome('failed','provider_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=[],payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    from ..module_contract import read_json,spatial_projection
    try:
        root=Path(result_path).parent;report=read_json(root/'native-exchange.json')
        request_path=Path(result['request']['path']);request=read_json(request_path)
        source=(request_path.parent/request['sources']['ifc']['path']).resolve()
        if read_json(root/'process.json')['returncode']!=0 or report['geometry']['ifc_sha256']!=digest(source):raise ValueError('Native spatial source/process differs')
        expected=spatial_projection(request['coordinate_frame'],report['geometry'],report['payload']['contacts'])
        if expected!=report['payload'] or expected!=result['payload']:raise ValueError('Common spatial payload differs from retained native audit')
    except (OSError,ValueError,KeyError,TypeError) as exc:raise ValueError('Invalid native spatial evidence: '+str(exc)) from exc
