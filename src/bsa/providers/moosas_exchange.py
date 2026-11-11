"""Thin isolated adapter for the existing pinned upstream MOOSAS exchange."""
import json
from pathlib import Path
import subprocess
import sys
from ..cli import digest

ROOT=Path(__file__).resolve().parents[3]
PIN='dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c'
CAPABILITY='spatial.ifc-boxes.exchange'
PAYLOAD='bsa.spatial-boxes/1'
DESCRIPTION=dict(id='moosas.box-space-exchange',version='1',upstream_commit=PIN,license='Apache-2.0')


def validate_request(request):
    if request['capability']!=CAPABILITY or set(request['sources'])!={'ifc','binding'}:raise ValueError('MOOSAS provider requires IFC-box exchange and exact ifc/binding sources')


def execute(request,paths,runtime,out):
    """Runtime configuration comes from host arguments,never the request document."""
    pins={};diagnostics=[];payload=None
    def outcome(status,code,message):return dict(status=status,diagnostics=[dict(code=code,message=message)],payload=None,pins=pins)
    upstream=runtime.get('upstream');deps=runtime.get('deps')
    if upstream is None or deps is None:return outcome('unavailable','runtime_missing','Explicit upstream and isolated dependency directories are required')
    upstream,deps=Path(upstream).resolve(),Path(deps).resolve()
    if not all(p.is_relative_to(ROOT) and p.is_dir() for p in (upstream,deps)):return outcome('unavailable','runtime_missing','Existing repository-local upstream and isolated dependency directories required')
    def checkout():
        head=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
        dirty=subprocess.check_output(['git','-C',str(upstream),'status','--porcelain'],text=True).strip()
        if head!=PIN or dirty:raise ValueError('Exact clean pinned MOOSAS checkout required')
    try:checkout()
    except (OSError,subprocess.SubprocessError,ValueError) as exc:return outcome('unavailable','upstream_incompatible',str(exc))
    tracked=subprocess.check_output(['git','-C',str(upstream),'ls-files','-z','--','MoosasPy','LICENSE','NOTICE']).decode().split('\0')
    for name in tracked:
        p=upstream/name
        if name and p.is_file() and (p.suffix in ('.py','.json') or p.name in ('LICENSE','NOTICE')):pins[str(p)]=digest(p)
    script=ROOT/'scripts/moosas_space_exchange.py'
    for p in (script,ROOT/'scripts/probe_moosas_ifc.py',Path(__file__),ROOT/'src/bsa/thermal_binding.py',ROOT/'src/bsa/thermal_geometry.py',ROOT/'src/bsa/annual_energy.py',ROOT/'src/bsa/box_geometry.py'):
        pins[str(p.resolve())]=digest(p)
    command=[sys.executable,str(script),'--ifc',str(paths['ifc']),'--binding',str(paths['binding']),'--upstream',str(upstream),'--deps',str(deps),'--out',str(out/'exchange')]
    try:
        process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    except OSError as exc:return outcome('unavailable','runtime_launch_failed',str(exc))
    except subprocess.TimeoutExpired as exc:return outcome('failed','provider_timeout',str(exc))
    (out/'provider.stdout.txt').write_text(process.stdout,encoding='utf-8');(out/'provider.stderr.txt').write_text(process.stderr,encoding='utf-8')
    (out/'process.json').write_text(json.dumps(dict(returncode=process.returncode,upstream_commit=PIN),indent=2))
    if process.returncode!=0:return outcome('failed','upstream_exchange_failed','MOOSAS exchange did not complete;inspect retained provider logs')
    report_path=out/'exchange/exchange.json'
    try:
        report=json.loads(report_path.read_text(encoding='utf-8'))
        if report['upstream_commit']!=PIN or report['geometry_exchange_pass'] is not True or not report['checks'] or not all(v is True for v in report['checks'].values()) or report['simulation_executed'] is not False:
            raise ValueError('Upstream scoped exchange checks did not pass')
        if report['inputs']!={str(p):digest(p) for p in paths.values()}:raise ValueError('Upstream report input identities differ')
        for name,sha in report['artifacts'].items():
            p=(out/'exchange'/name).resolve()
            if not p.is_relative_to(out/'exchange') or digest(p)!=sha:raise ValueError('Upstream exchange artifact differs')
        payload=dict(schema=PAYLOAD,coordinate_frame=request['coordinate_frame'],units=dict(length='m',area='m2'),classification='geometry-derived',
            spaces=[dict(id=r['guid'],origin_m=r['origin_m'],size_m=r['size_m'],floor_area_m2=r['floor_area_m2']) for r in report['geometry']['spaces']],
            contacts=report['geometric_contacts'],simulation_ready=False)
        checkout()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:return outcome('failed','provider_evidence_invalid',str(exc))
    return dict(status='completed',diagnostics=diagnostics,payload=payload,pins=pins)


def verify_evidence(result,result_path):
    if result['execution']['status']!='completed':return
    from ..module_contract import read_json,spatial_projection
    try:
        root=Path(result_path).parent;report=read_json(root/'exchange/exchange.json')
        request_path=Path(result['request']['path']);request=read_json(request_path)
        paths={k:(request_path.parent/r['path']).resolve() for k,r in request['sources'].items()}
        if report['inputs']!={str(p):digest(p) for p in paths.values()}:raise ValueError('MOOSAS retained input identity differs')
        process=read_json(root/'process.json')
        if process['returncode']!=0 or process['upstream_commit']!=PIN or report['upstream_commit']!=PIN:raise ValueError('MOOSAS process/pin differs')
        if report['geometry_exchange_pass'] is not True or report['simulation_executed'] is not False or not report['checks'] or not all(v is True for v in report['checks'].values()):raise ValueError('MOOSAS scoped exchange did not pass')
        if report['geometry']['ifc_sha256']!=digest(paths['ifc']):raise ValueError('MOOSAS geometry source differs')
        expected=spatial_projection(request['coordinate_frame'],report['geometry'],report['geometric_contacts'])
        if expected!=result['payload']:raise ValueError('Common spatial payload differs from retained MOOSAS audit')
    except (OSError,ValueError,KeyError,TypeError) as exc:raise ValueError('Invalid MOOSAS spatial evidence: '+str(exc)) from exc
