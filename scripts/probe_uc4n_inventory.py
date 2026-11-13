"""Use the pinned independent DXF backend after trusted native DWG export."""
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


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

async def run(source,baseline,out):
    root=Path(os.environ['BSA_PROJECT_ROOT']).resolve()
    source,baseline,out=[Path(p).resolve() for p in (source,baseline,out)]
    if root==Path(root.anchor) or any(not p.is_relative_to(root) for p in (source,baseline,out)) or out.exists() or source.suffix.lower()!='.dxf':raise ValueError('Selected project DXF/baseline and fresh output required')
    head=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(UPSTREAM),'status','--porcelain'],text=True).strip()
    if head!=COMMIT or dirty:raise ValueError('Exact clean reviewed upstream required')
    versions={p:importlib.metadata.version(p) for p in ['ezdxf','pydantic','numpy']}
    if versions!={'ezdxf':'1.4.5','pydantic':'2.14.3','numpy':'2.5.4'}:raise ValueError('Reviewed dependency versions required')
    out.mkdir(parents=True);before=sha(source);base_before=sha(baseline)
    os.environ['CAD_LAUNCH']='never';sys.path.insert(0,str(UPSTREAM))
    from backends.ezdxf_backend import EzdxfBackend
    backend=EzdxfBackend();await backend.connect()
    try:
        opened=await backend.drawing_open(str(source))
        info=asdict(await backend.drawing_info());layers=[asdict(v) for v in await backend.layer_list()]
        layouts=await backend.layout_list();blocks=[asdict(v) for v in await backend.block_list()]
        entities=[]
        while True:
            page=await backend.entity_list(limit=500,offset=len(entities))
            if not page:break
            entities.extend(asdict(v) for v in page)
        base=json.loads(baseline.read_text());expected={r['handle']:(r['type'],r['layer']) for r in base['entities']}
        actual={r['handle']:(r['type'],r['layer']) for r in entities}
        checks=dict(handles_types_layers_match=actual==expected and len(entities)==len(expected),layer_table_match={r['name'] for r in layers}=={r['name'] for r in base['layers']},source_unchanged=sha(source)==before,baseline_unchanged=sha(baseline)==base_before)
        record=dict(scope='Pinned upstream DXF backend on native-exported real DWG; read-only inventory correspondence, not native write/plot or design acceptance',upstream_commit=COMMIT,versions=versions,source_sha256=before,baseline_sha256=base_before,drawing_open=opened,info=info,layers=layers,layouts=layouts,blocks=blocks,entities=entities,checks=checks,design_accepted=False)
        (out/'inventory.json').write_text(json.dumps(record,indent=2,default=str),encoding='utf-8')
        if not all(checks.values()):raise ValueError('Actual upstream inventory correspondence failed')
        print(json.dumps(dict(entities=len(entities),layers=len(layers),layouts=layouts,checks=checks,design_accepted=False),indent=2))
    finally:await backend.disconnect()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['source','baseline','out']:parser.add_argument('--'+key,required=True)
    a=parser.parse_args();asyncio.run(run(a.source,a.baseline,a.out))
