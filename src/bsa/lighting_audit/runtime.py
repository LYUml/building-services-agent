"""Fixed read-only CLI bridge into the user-provisioned pinned DIALux toolkit."""
import json
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess

from ..source_refs import file_hash

COMMIT='ade128b7ae446c6ea253776a5ead866280d6bf4a'
FILES=('src/dialux_agent.py','src/results.py','requirements-lock.txt')


def configuration():
    name=os.environ.get('BSA_DIALUX_TOOLKIT_ROOT')
    if not name:raise ValueError('Host BSA_DIALUX_TOOLKIT_ROOT is required for the existing external reader')
    root=Path(name)
    if not root.is_absolute() or not root.is_dir():raise ValueError('Existing absolute host toolkit root required')
    try:
        if importlib.metadata.version('pypdf')!='7.0.0':raise ValueError('Pinned host pypdf7.0.0 documents profile required')
    except importlib.metadata.PackageNotFoundError as exc:raise ValueError('Host documents profile is required') from exc
    root=root.resolve();git=shutil.which('git')
    if not git:raise ValueError('Host Git required to verify the pinned reader')
    env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
    def read(*args):
        p=subprocess.run([git,'-C',str(root),*args],capture_output=True,env=env,timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if p.returncode:raise ValueError('Cannot verify external toolkit Git state')
        return p.stdout.decode('utf-8').strip()
    if Path(read('rev-parse','--show-toplevel')).resolve()!=root:
        raise ValueError('Exact external toolkit checkout required')
    if read('rev-parse','HEAD')!=COMMIT or read('status','--porcelain','--untracked-files=no'):
        raise ValueError('Pinned clean external toolkit revision required; do not bypass its guards')
    python=root/('.venv/Scripts/python.exe' if os.name=='nt' else '.venv/bin/python')
    files=[python,*[root/p for p in FILES]]
    if any(not p.is_file() for p in files):raise ValueError('Existing toolkit interpreter/source profile missing')
    return root,python,{str(p):file_hash(p) for p in files}


def external_inputs():
    try:return {Path(p) for p in configuration()[2]}
    except (ValueError,OSError,subprocess.SubprocessError):return set()


def read_summary(pdf,pages,header,out):
    root,python,pins=configuration()
    from pypdf import PdfReader,PdfWriter
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    reader=PdfReader(pdf);writer=PdfWriter()
    if len(pages)!=2 or pages[1]!=pages[0]+1 or any(type(n) is not int or not 1<=n<=len(reader.pages) for n in pages):
        raise ValueError('Two explicit adjacent physical native summary pages required')
    for n in pages:writer.add_page(reader.pages[n-1])
    excerpt=out/'excerpt.pdf'
    with excerpt.open('xb') as stream:writer.write(stream)
    writer.close()
    reader.close()
    p=subprocess.run([str(python),'-X','utf8','-m','src.dialux_agent','report-read','--path',str(excerpt.resolve())],
        cwd=root,capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    (out/'stdout.json').write_bytes(p.stdout);(out/'stderr.log').write_bytes(p.stderr)
    if p.returncode:raise ValueError('Pinned native-summary reader rejected the selected source: '+p.stdout.decode('utf-8',errors='replace')[-600:])
    raw=json.loads(p.stdout.decode('utf-8'))
    if raw.get('room_scene_header')!=header:raise ValueError('External reader room identity differs')
    measures=[]
    for row in raw['measurements']:
        row=dict(row);row.pop('evidence',None)
        row['page']=pages[row['page']-1];measures.append(row)
    normalized={k:raw[k] for k in ('room_scene_header','area_m2','height_m','workplane_m','compliance_status','warnings','unavailable_measurements')}
    normalized.update(measurements=measures,original_pages=pages,original_sha256=file_hash(pdf),
        excerpt_sha256=file_hash(excerpt),upstream_commit=COMMIT,fresh_native_calculation=False)
    if configuration()[2]!=pins:raise ValueError('External reader changed during extraction')
    return normalized,pins
