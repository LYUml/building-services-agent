"""Native DWG intake plus a pinned independent upstream DXF inspection backend."""
import argparse
import json
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
from . import cad_intake,workspace,native_cad
from .cli import digest

WORKER=workspace.ROOT/'scripts/probe_uc4n_inventory.py'
UPSTREAM=workspace.ROOT/'tools/autocad-uc4n-review'
COMMIT='6f6a538255ca9f885232e845ac32f10b4433fe3e'
SCOPE='Native-exported source inventory with pinned upstream DXF inspection; not physical scale, design, native write or plot acceptance'


def local(path,output=False):
    path=Path(path).resolve();root=workspace.project_root() or workspace.ROOT
    if not path.is_relative_to(root) or output and workspace.project_root() is None and not path.is_relative_to(workspace.ROOT/'runs'):raise ValueError('Host-selected source/output workspace required')
    if output and path.is_relative_to(workspace.ROOT.parent/'polyu_bse3124'):raise ValueError('Historical coursework is read-only')
    return path


def run(source,out,*,autocad=None):
    source,out=local(source),local(out,True)
    if source.suffix.lower() not in ('.dwg','.dxf') or not source.is_file() or out.exists() or out==source or out in source.parents:raise ValueError('Existing source and fresh separate output required')
    head=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
    if head!=COMMIT or subprocess.check_output(['git','-C',str(UPSTREAM),'status','--porcelain'],text=True).strip():raise ValueError('Clean pinned upstream checkout required')
    pins={str(p):digest(p) for p in [source,Path(__file__),WORKER,Path(cad_intake.__file__),Path(native_cad.__file__),Path(workspace.__file__)]}
    engine=Path(autocad).resolve() if autocad is not None else None
    if source.suffix.lower()=='.dwg':
        if engine is None or not engine.is_file():raise ValueError('Explicit host AutoCAD executable required for DWG')
        pins[str(engine)]=digest(engine)
    out.mkdir(parents=True)
    result=dict(schema='bsa.autocad-source/1',scope=SCOPE,source=str(source),upstream_commit=COMMIT,inputs=pins,status='failed',design_accepted=False)
    try:
        cad_intake.run(source,out/'native-intake',exe=engine)
        export=out/'native-intake'/('native/source-export.dxf' if source.suffix.lower()=='.dwg' else 'source-copy.dxf')
        copied=out/'upstream-input.dxf';shutil.copyfile(export,copied)
        temp=out/'temp';temp.mkdir()
        root=workspace.project_root() or workspace.ROOT
        env={**os.environ,'BSA_PROJECT_ROOT':str(root),'CAD_LAUNCH':'never','TEMP':str(temp),'TMP':str(temp)}
        completed=subprocess.run([sys.executable,'-X','utf8',str(WORKER),'--source',str(copied),'--baseline',str(out/'native-intake/inventory.json'),'--out',str(out/'upstream')],cwd=workspace.ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
        (out/'upstream.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        result['worker_returncode']=completed.returncode
        if completed.returncode:raise ValueError('Upstream inspection failed; inspect upstream.log')
        result['status']='inspected'
    except Exception as exc:result['error']=type(exc).__name__+': '+str(exc)
    result['inputs_unchanged']=all(Path(p).is_file() and digest(Path(p))==sha for p,sha in pins.items())
    if not result['inputs_unchanged']:result['status']='source_changed'
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'inspection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def verify(out):
    out=local(out);record=json.loads((out/'inspection.json').read_text())
    if record.get('schema')!='bsa.autocad-source/1' or record.get('scope')!=SCOPE or record.get('status')!='inspected' or record.get('worker_returncode')!=0 or record.get('design_accepted') is not False or record.get('inputs_unchanged') is not True:raise ValueError('Completed unaccepted inspection required')
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in record['inputs'].items()):raise ValueError('Source, engine or inspection methods changed')
    for name,sha in record['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or not path.is_file() or digest(path)!=sha:raise ValueError('Inspection artifact changed or missing')
    head=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
    if head!=COMMIT or record.get('upstream_commit')!=COMMIT or subprocess.check_output(['git','-C',str(UPSTREAM),'status','--porcelain'],text=True).strip():raise ValueError('Upstream source changed')
    baseline=json.loads((out/'native-intake/inventory.json').read_text());saved=json.loads((out/'upstream/inventory.json').read_text())
    expected=cad_intake.inventory(out/'upstream-input.dxf')
    canonical={r['handle']:(r['type'],r['layer']) for r in expected['entities']}
    actual={r['handle']:(r['type'],r['layer']) for r in saved['entities']}
    if saved.get('versions')!={p:importlib.metadata.version(p) for p in ['ezdxf','pydantic','numpy']} or saved.get('upstream_commit')!=COMMIT:raise ValueError('Upstream runtime versions differ')
    if canonical!={r['handle']:(r['type'],r['layer']) for r in baseline['entities']} or actual!=canonical or len(actual)!=len(saved['entities']) or {r['name'] for r in saved['layers']}!={r['name'] for r in expected['layers']}:raise ValueError('Saved upstream inventory differs from exported source')
    import ezdxf
    doc=ezdxf.readfile(out/'upstream-input.dxf')
    if saved['layouts']['layouts']!=list(doc.layouts.names_in_taborder()):raise ValueError('Upstream layout coverage differs from source')
    return dict(integrity_pass=True,entities=len(actual),layers=len(saved['layers']),layouts=len(saved['layouts']['layouts']),insunits=expected['insunits'],design_accepted=False,scope=SCOPE)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    command=sub.add_parser('run');command.add_argument('source');command.add_argument('--out',required=True);command.add_argument('--autocad')
    sub.add_parser('verify').add_argument('out');args=parser.parse_args()
    result=verify(args.out) if args.command=='verify' else run(args.source,args.out,autocad=args.autocad)
    print(json.dumps(result if args.command=='verify' else {k:result[k] for k in ['status','inputs_unchanged','design_accepted']},indent=2))
    return 0 if args.command=='verify' or result['status']=='inspected' else 2

if __name__=='__main__':raise SystemExit(main())
