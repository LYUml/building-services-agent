"""Fixed typed upstream schedule writer; no arbitrary CAD command execution."""
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
UPSTREAM=ROOT/'tools/autocad-uc4n-review'
COMMIT='6f6a538255ca9f885232e845ac32f10b4433fe3e'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

async def run(path):
    root=Path(os.environ['BSA_PROJECT_ROOT']).resolve();path=Path(path).resolve()
    if not path.is_relative_to(root):raise ValueError('Host project request required')
    request=json.loads(path.read_text())
    source,target=[Path(request[k]).resolve() for k in ('source','target')]
    if not all(p.is_relative_to(root) for p in [source,target]) or target.exists() or source==target or target.suffix.lower()!='.dxf' or sha(source)!=request['source_sha256']:raise ValueError('Unchanged source and fresh project DXF target required')
    if subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()!=COMMIT or subprocess.check_output(['git','-C',str(UPSTREAM),'status','--porcelain'],text=True).strip():raise ValueError('Clean pinned upstream required')
    versions={p:importlib.metadata.version(p) for p in ['ezdxf','pydantic','numpy']}
    if versions!={'ezdxf':'1.4.5','pydantic':'2.14.3','numpy':'2.5.4'}:raise ValueError('Reviewed upstream runtime required')
    os.environ['CAD_LAUNCH']='never';sys.path.insert(0,str(UPSTREAM))
    from backends.ezdxf_backend import EzdxfBackend
    backend=EzdxfBackend();await backend.connect()
    try:
        await backend.drawing_open(str(source))
        for row in request['edits']:
            info=await backend.entity_get(row['handle'])
            if info.type!='TEXT' or info.properties.get('text')!=row['before']:raise ValueError('Source TEXT differs from explicit validated binding')
        for row in request['edits']:await backend.entity_edit_text(row['handle'],text=row['text'])
        if request['arrows']:
            await backend.layer_create(request['arrow_layer'],color=7)
            for row in request['arrows']:
                a,b=row['start'],row['end']
                await backend.entity_create_line(a[0],a[1],b[0],b[1],z1=a[2],z2=b[2],layer=request['arrow_layer'])
        saved=await backend.drawing_save_as(str(target))
    finally:await backend.disconnect()
    if sha(source)!=request['source_sha256']:raise ValueError('Input drawing changed')
    result=dict(upstream_commit=COMMIT,versions=versions,source_unchanged=True,target_sha256=sha(target),edited_cells=len(request['edits']),arrow_lines=len(request['arrows']),save=saved,design_accepted=False)
    (path.parent/'writer.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['edited_cells','arrow_lines','source_unchanged','design_accepted']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request');asyncio.run(run(parser.parse_args().request))
