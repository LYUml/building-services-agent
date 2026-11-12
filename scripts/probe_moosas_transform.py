"""Execute pinned MOOSAS surface-to-space recognition; no simulation or design acceptance.

KLEGB/MOOSAS is Apache-2.0; upstream source remains unmodified. The optional
empty catalogue is an explicit geometry-only resource compatibility override.
"""
import argparse
import contextlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import traceback
from probe_moosas_ifc import PIN, digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','upstream','deps','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--empty-catalogue',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    source,upstream,deps,out=(getattr(args,k).resolve() for k in ('source','upstream','deps','out'))
    if any(not p.is_relative_to(root) for p in (source,upstream,deps,out)) or out.exists():
        parser.error('Repository-local source/runtime and new output directory required')
    if out.is_relative_to(upstream) or out.is_relative_to(deps) or any(p.is_relative_to(out) for p in (source,upstream,deps)):
        parser.error('Output must remain separate from source and upstream/dependency installations')
    if subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()!=PIN:
        parser.error('Pinned upstream commit required')
    if subprocess.check_output(['git','-C',str(upstream),'status','--porcelain'],text=True).strip():
        parser.error('Clean upstream checkout required')
    if source.suffix.lower() not in ('.geo','.obj','.stl'):parser.error('Explicit supported surface geometry required')
    helper=Path(__file__).with_name('probe_moosas_ifc.py').resolve()
    before={str(source):digest(source),str(Path(__file__).resolve()):digest(Path(__file__)),str(helper):digest(helper)}
    before.update({str(p):digest(p) for p in (upstream/'MoosasPy').rglob('*.py')})
    before.update({str(p):digest(p) for p in (upstream/'MoosasPy').rglob('*.json')})
    before[str(upstream/'LICENSE')]=digest(upstream/'LICENSE')
    out.mkdir(parents=True)
    sys.path[:0]=[str(upstream),str(deps)]
    result=dict(upstream_commit=PIN,inputs=before,empty_catalogue_override=args.empty_catalogue,
        spaces=[],execution='failed',simulation_executed=False,design_accepted=False,
        scope='Surface-to-space recognition probe;not architectural correctness,MEP or thermal readiness')
    with (out/'worker.log').open('w',encoding='utf-8') as log:
        try:
            with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                versions={name:importlib.metadata.version(name) for name in ('rdflib','pyparsing','shapely')}
                result['dependencies']=versions
                if versions!={'rdflib':'7.1.4','pyparsing':'3.2.3','shapely':'2.2.0'}:
                    raise ValueError('Pinned geometry exchange dependencies required')
                from MoosasPy.transform import pipeline
                original=pipeline.configure_model_resources
                try:
                    if args.empty_catalogue:
                        catalogue=out/'geometry-only-catalogue';catalogue.mkdir()
                        (catalogue/'library.json').write_text(json.dumps(dict(schema='moosas.building-template-library',version=5,standards=[])),encoding='utf-8')
                        def resources(model):
                            return original(model,template_path=str(catalogue))
                        pipeline.configure_model_resources=resources
                    model=pipeline.transform(str(source),stdout=log)
                    from shapely import get_coordinates
                    for space in model.spaceList:
                        result['spaces'].append(dict(id=str(space.id),area_m2=float(space.area),height_m=float(space.height),
                            is_open=bool(space.is_open()),boundary_vertices=get_coordinates(space.force_2d()).tolist()))
                    model.save(str(out/'recognized.xml'))
                    from MoosasPy.model import MoosasModel
                    building_templates=importlib.import_module('MoosasPy.model.building_templates')
                    previous=building_templates.DEFAULT_LIBRARY
                    try:
                        if args.empty_catalogue:building_templates.DEFAULT_LIBRARY=catalogue
                        loaded=MoosasModel.load(out/'recognized.xml')
                    finally:
                        building_templates.DEFAULT_LIBRARY=previous
                    actual=[dict(id=str(s.id),area_m2=float(s.area),height_m=float(s.height),is_open=bool(s.is_open()),
                        boundary_vertices=get_coordinates(s.force_2d()).tolist()) for s in loaded.spaceList]
                    result['saved_reload_matches']=sorted(actual,key=lambda r:r['id'])==sorted(result['spaces'],key=lambda r:r['id'])
                    if not result['saved_reload_matches']:raise ValueError('Saved recognized spaces differ after native XML reload')
                    result['execution']='completed'
                finally:
                    pipeline.configure_model_resources=original
        except Exception as exc:
            result['diagnostic']=dict(type=type(exc).__name__,message=str(exc))
            traceback.print_exc(file=log)
    if any(digest(Path(p))!=sha for p,sha in before.items()):raise ValueError('Source or upstream changed during probe')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(result['execution'],len(result['spaces']),'recognized spaces;engineering acceptance pending')
    return 0 if result['execution']=='completed' else 2


if __name__=='__main__':raise SystemExit(main())
