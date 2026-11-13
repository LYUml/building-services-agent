"""Controlled public-mesh storage comparison, retaining full native/schema checks."""
import argparse
from contextlib import nullcontext
import importlib.metadata
import json
from pathlib import Path
import time
from unittest.mock import patch
import ifcopenshell
from ifcopenshell.util.shape_builder import ShapeBuilder
from bsa import bim,circular_elbow
from bsa.cli import digest
from bsa.workspace import ROOT


def run(out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh public benchmark output required')
    source=ROOT/'examples/circular-elbow/project.json'
    files=[source,Path(bim.__file__),Path(circular_elbow.__file__),Path(ShapeBuilder.triangulated_face_set.__code__.co_filename)]
    pins={str(p):digest(p) for p in files};out.mkdir(parents=True)
    rows={};meshes={};identities={}
    for name in ['compact','legacy_polygonal']:
        mode=nullcontext() if name=='compact' else patch.object(ShapeBuilder,'triangulated_face_set',ShapeBuilder.polygonal_face_set)
        start=time.perf_counter()
        with mode:checked=bim.run(source,out/name)
        elapsed=time.perf_counter()-start
        saved=out/name/'model.ifc';model=ifcopenshell.open(str(saved))
        elbow=next(o for o in model.by_type('IfcPipeFitting') if o.PredefinedType=='BEND')
        body=next(r for r in elbow.Representation.Representations if r.RepresentationIdentifier=='Body').Items[0]
        faces=[list(f) for f in body.CoordIndex] if body.is_a('IfcTriangulatedFaceSet') else [list(f.CoordIndex) for f in body.Faces]
        meshes[name]=(body.Coordinates.CoordList,faces)
        identities[name]=[(r['id'],r['global_id'],r['space'],r['systems']) for r in checked['devices']]
        rows[name]=dict(seconds=elapsed,file_bytes=saved.stat().st_size,entity_count=sum(1 for _ in model),body_class=body.is_a(),vertices=len(body.Coordinates.CoordList),triangles=len(faces),model_checks_pass=checked['model_checks_pass'],checks=checked['checks'],ifc_sha256=digest(saved),devices=checked['devices'])
    if meshes['compact']!=meshes['legacy_polygonal'] or identities['compact']!=identities['legacy_polygonal']:raise ValueError('Storage change altered exact source mesh or device identities')
    if not all(digest(Path(p))==sha for p,sha in pins.items()):raise ValueError('Benchmark source or method changed')
    result=dict(scope='One synthetic public elbow, unprofiled end-to-end author/save/reopen/native/schema comparison; no whole-workflow speed guarantee',runtime_ifcopenshell=importlib.metadata.version('ifcopenshell'),inputs=pins,cases=rows,exact_coordinates_and_triangles_preserved=True,device_identity_space_system_preserved=True,design_accepted=False)
    (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:{f:r[f] for f in ['seconds','file_bytes','entity_count','body_class','vertices','triangles','model_checks_pass']} for k,r in rows.items()},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);run(parser.parse_args().out)
