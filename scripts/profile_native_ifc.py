"""Windows fresh-process native route probe; synthetic fixture, not a design.

Requires the existing pinned [drawing,bim] profile. Compares the original default
native factory and guarded production path using unchanged source checks.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import zipfile
from windows_memory_probe import MEMORY_CODE

ROOT=Path(__file__).resolve().parents[1]
CHILD=r"""
import sys,os,time,json,ctypes,asyncio,subprocess
from unittest.mock import patch
"""+MEMORY_CODE+r"""
from pathlib import Path
before=memory();start=time.perf_counter()
import ifcopenshell,ifcopenshell.geom
from bsa import circular_geometry
from bsa.ifc_route_drawing import extract
if ifcopenshell.version!='0.8.5':raise RuntimeError('Pinned IfcOpenShell0.8.5 required')
root=Path.cwd();mode=sys.argv[1]
if mode=='original':circular_geometry.native_shape=lambda settings,obj:ifcopenshell.geom.create_shape(settings,obj)
model=json.loads((root/'examples/circular-elbow/project.json').read_text())
settings=json.loads((root/'examples/circular-elbow/drawing-settings.json').read_text())
pieces=extract(Path(sys.argv[2]),model,settings)
print(json.dumps(dict(mode=mode,seconds=time.perf_counter()-start,before=before,after=memory(),ifcopenshell=ifcopenshell.version,pieces=pieces),allow_nan=False))
"""


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def compare(a,b):
    if type(a)!=type(b):raise ValueError('Native probe result types differ')
    if type(a) in (int,float):
        if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>1e-12:raise ValueError('Native probe numerical results differ')
    elif isinstance(a,dict):
        if set(a)!=set(b):raise ValueError('Native probe result fields differ')
        for key in a:compare(a[key],b[key])
    elif isinstance(a,list):
        if len(a)!=len(b):raise ValueError('Native probe result coverage differs')
        for left,right in zip(a,b):compare(left,right)
    elif a!=b:raise ValueError('Native probe result facts differ')


def run(out,trials):
    out=Path(out).resolve()
    if sys.platform!='win32':raise ValueError('Windows process-memory counters required')
    if type(trials) is not int or not 1<=trials<=10:raise ValueError('Trials must be1..10')
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh repository runs output required')
    archive=ROOT/'docs/evidence/circular-elbow/workflow.zip'
    paths=[archive,ROOT/'examples/circular-elbow/project.json',ROOT/'examples/circular-elbow/drawing-settings.json',
        ROOT/'src/bsa/circular_geometry.py',ROOT/'src/bsa/circular_elbow.py',ROOT/'src/bsa/ifc_route_drawing.py',
        ROOT/'scripts/profile_native_ifc.py',ROOT/'scripts/windows_memory_probe.py']
    def pins():return {p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    before=pins();out.mkdir(parents=True);fixture=out/'source.ifc'
    with zipfile.ZipFile(archive) as saved:fixture.write_bytes(saved.read('model/bim/model.ifc'))
    fixture_hash=digest(fixture);rows=[]
    for trial in range(trials):
        for mode in ['original','guarded']:
            environment=dict(os.environ);environment.pop('BSA_PROJECT_ROOT',None)
            result=subprocess.run([sys.executable,'-X','utf8','-c',CHILD,mode,str(fixture)],cwd=ROOT,
                env=environment,capture_output=True,text=True,encoding='utf-8',timeout=600)
            for name,value in [('stdout',result.stdout),('stderr',result.stderr)]:
                (out/f'trial-{trial+1}-{mode}.{name}.log').write_text(value,encoding='utf-8')
            if result.returncode:raise RuntimeError('Native probe failed; retained child logs at '+str(out))
            row=json.loads(result.stdout);row['trial']=trial+1;rows.append(row)
    if pins()!=before or digest(fixture)!=fixture_hash:raise ValueError('Native probe source changed')
    for row in rows:compare(row['pieces'],rows[0]['pieces'])
    summary={mode:dict(median_seconds=statistics.median(r['seconds'] for r in rows if r['mode']==mode),
        median_peak_bytes=statistics.median(r['after']['peak_bytes'] for r in rows if r['mode']==mode)) for mode in ['original','guarded']}
    report=dict(schema='bsa.native-ifc-resource-probe/1',recorded_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256=before,fixture_sha256=fixture_hash,rows=rows,summary=summary,source_unchanged=True,
        pieces_equal_within_1e_12=True,scope='Windows fresh Python process peak working set and import/read/extract time for a synthetic three-piece route; not total host, AutoCAD, real project, Linux or general-engine performance',design_accepted=False)
    (out/'measurements.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--trials',type=int,default=3);args=parser.parse_args()
    result=run(args.out,args.trials);print(json.dumps(result['summary'],indent=2))
