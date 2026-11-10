"""Thin source/native binding to the isolated AGPL Honeybee scene adapter."""
import json
from pathlib import Path
import subprocess
from .cli import digest
from .engine import ProjectError
from .concept_layout import geometry_handoff,validate_settings
from .concept_facade import inspect,settings as facade_settings
ROOT=Path(__file__).resolve().parents[2]


def validate_basis(s):
    if set(s)!={'source','documents','reflectance','visible_transmittance','grid_spacing_m','sensor_height_m'} or not isinstance(s['source'],str) or not s['source'].strip():raise ProjectError('explicit source-backed scene settings required')
    if set(s['reflectance'])!={'wall','floor','ceiling'} or any(type(v) not in (int,float) or not 0<v<1 for v in s['reflectance'].values()) or type(s['visible_transmittance']) not in (int,float) or not 0<s['visible_transmittance']<1:raise ProjectError('explicit optical fractions required')
    if any(type(s[k]) not in (int,float) or not .01<=s[k]<=2 for k in ('grid_spacing_m','sensor_height_m')):raise ProjectError('bounded explicit sensor spacing/height required')
    if not isinstance(s['documents'],dict) or not s['documents']:raise ProjectError('source documents with hashes required')
    return s


def source_files(scene_basis):
    scene_basis=Path(scene_basis).resolve()
    s=validate_basis(json.loads(scene_basis.read_text(encoding='utf-8-sig')));files={scene_basis}
    for name,sha in s['documents'].items():
        path=(scene_basis.parent/name).resolve()
        if not path.is_relative_to(scene_basis.parent) or not path.is_file() or digest(path)!=sha:raise ProjectError('scene source document identity differs')
        files.add(path)
    return files


def run(ifc,project,layout,facade_basis,scene_basis,out,python):
    import ifcopenshell
    ifc,project,layout,facade_basis,scene_basis,out,python=map(lambda p:Path(p).resolve(),(ifc,project,layout,facade_basis,scene_basis,out,python))
    worker=ROOT/'adapters/honeybee-scene/worker.py';lock=worker.parent/'dependencies.json'
    pins={str(p):digest(p) for p in (ifc,project,layout,facade_basis,scene_basis,python,worker,lock)}
    source=json.loads(project.read_text(encoding='utf-8-sig'));l=validate_settings(json.loads(layout.read_text(encoding='utf-8-sig')))
    b=facade_settings(json.loads(facade_basis.read_text(encoding='utf-8-sig')));s=json.loads(scene_basis.read_text(encoding='utf-8-sig'))
    pins.update({str(p):digest(p) for p in source_files(scene_basis)})
    handoff=geometry_handoff(ifc,source,l['window_wall_ratio']);inspect(ifcopenshell.open(str(ifc)),source,handoff,b)
    packet=dict(adjacency=handoff['adjacency'],settings=s,spaces=[dict(id=r['thermal_id'],origin_m=r['origin_m'],size_m=r['size_m'],source='Saved native concept facade; geometry interpretation only') for r in handoff['geometry']['spaces']],windows=handoff['draft_window_rectangles'],window_area_m2=handoff['draft_window_area_m2'],ifc_sha256=digest(ifc))
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ProjectError('separate scene output required')
    out.mkdir(parents=True,exist_ok=False);input=out/'packet.json';input.write_text(json.dumps(packet,indent=2),encoding='utf-8')
    packet_sha=digest(input)
    with (out/'worker.log').open('wb') as log:r=subprocess.run([str(python),str(worker),str(input),str(out/'scene')],stdout=log,stderr=subprocess.STDOUT,timeout=120)
    if r.returncode:raise ProjectError('Honeybee scene adapter failed; inspect worker.log')
    result=json.loads((out/'scene/scene.json').read_text(encoding='utf-8'))
    if digest(input)!=packet_sha or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('scene source changed during conversion')
    result.update(inputs=pins,artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()})
    (out/'honeybee-scene.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('ifc','project','layout','facade-basis','scene-basis','out','python'):parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    result=run(args.ifc,args.project,args.layout,args.facade_basis,args.scene_basis,args.out,args.python)
    print(json.dumps({k:result[k] for k in ('rooms','apertures','sensor_count','geometry_checks_pass','simulation_executed','solver_ready','design_accepted')},indent=2))
