"""Derive an electrical project from verified straight/quarter-circle IFC lengths."""
import argparse
import copy
import json
from pathlib import Path
import shutil

from .cli import digest
from .engine import ProjectError
from .three_phase import prepare,ROOT
from .three_phase_ifc import inspect


def run(project,ifc,binding,out,python=None):
    project,ifc,binding,out=[Path(v).resolve() for v in (project,ifc,binding,out)]
    baseline,files=prepare(project)
    # Only the old numerical length is allowed to differ. Body/Axis/ports,
    # placement, native solid checks and analysis bus anchors remain mandatory.
    observed=inspect(project,ifc,binding,require_length_match=False)
    if observed['native_geometry_checks_pass'] is not True:raise ProjectError('verified native geometry required')
    originals={**observed['inputs'],str(Path(__file__).resolve()):digest(Path(__file__))}
    if not out.is_relative_to(ROOT) or out.exists() or any(out==Path(f) or out in Path(f).parents for f in originals):
        raise ProjectError('new separate repository output required')
    source_ids={}
    for name in ('ifc_route_lengths','ifc_model','ifc_binding','ifc_geometry_basis'):
        key=name;index=2
        while key in baseline['sources'] or key in source_ids.values():key=f'{name}_{index}';index+=1
        source_ids[name]=key
    out.mkdir(parents=True)
    for source in files:
        destination=out/'baseline'/source.relative_to(project.parent)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    model_dir=out/'model';model_dir.mkdir()
    shutil.copyfile(ifc,model_dir/'cables.ifc');shutil.copyfile(binding,model_dir/'binding.json')
    b=json.loads(binding.read_text(encoding='utf-8-sig'))
    geometry_relative=Path(b['source']['path'])
    # Avoid overwriting either copied native input with a malicious basis path.
    target=(model_dir/geometry_relative).resolve()
    if not target.is_relative_to(model_dir) or target in (model_dir/'cables.ifc',model_dir/'binding.json'):
        raise ProjectError('geometry basis must be separate from model and binding')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(binding.parent/geometry_relative,target)
    trace=out/'route-lengths.json'
    trace.write_text(json.dumps(observed,indent=2),encoding='utf-8')
    derived=copy.deepcopy(baseline)
    for value in derived['sources'].values():value['path']=(Path('baseline')/value['path']).as_posix()
    kind=b['source']['kind']
    for key,path,locator in (
        ('ifc_route_lengths',trace,'lines[].observed_length_m; actual IFC Axis/Body/port/native-solid checks'),
        ('ifc_model',model_dir/'cables.ifc','Saved selected-system straight cable solids and ports'),
        ('ifc_binding',model_dir/'binding.json','Explicit cable GUIDs, bus anchors and original geometry source'),
        ('ifc_geometry_basis',target,b['source']['locator'])):
        derived['sources'][source_ids[key]]=dict(path=path.relative_to(out).as_posix(),sha256=digest(path),locator=locator,kind=kind)
    by_id={r['id']:r for r in observed['lines']}
    changes=[]
    for line in derived['lines']:
        old=line['length_m'];line['length_m']=by_id[line['id']]['observed_length_m'];line['length_source']=source_ids['ifc_route_lengths']
        changes.append(dict(id=line['id'],baseline_length_m=old,derived_length_m=line['length_m']))
    derived_path=out/'project.json'
    derived_path.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    prepare(derived_path)
    checked=inspect(derived_path,model_dir/'cables.ifc',model_dir/'binding.json')
    (out/'derived-ifc-check.json').write_text(json.dumps(checked,indent=2),encoding='utf-8')
    study=None
    if python:
        from .three_phase_bridge import run as solve
        study=solve(derived_path,out/'study',python)
    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in originals.items()):raise ProjectError('original inputs changed during derivation')
    _,derived_files=prepare(derived_path)
    report=dict(original_inputs=originals,original_inputs_unchanged=True,changes=changes,
                derived_project_sha256=digest(derived_path),derived_inputs={str(f):digest(f) for f in derived_files},
                derived_geometry_correspondence_pass=checked['geometry_correspondence_pass'],
                numerical_status=study['status'] if study else 'pending',design_accepted=False,
                scope='New snapshot project with supported native straight, quarter-circle or quarter-plus-tangent IFC route lengths only; other electrical data preserved, no automatic cable selection, protection or physical connectivity')
    (out/'derivation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for key in ('ifc','binding','out'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--python',type=Path)
    a=parser.parse_args();result=run(a.project,a.ifc,a.binding,a.out,a.python)
    print(json.dumps({k:result[k] for k in ('derived_geometry_correspondence_pass','numerical_status','design_accepted')}))
    raise SystemExit(2 if result['numerical_status']=='fail' else 0)
