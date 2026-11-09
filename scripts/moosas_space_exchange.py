"""Exchange verified IFC box-space envelopes with pinned MOOSAS XML/GEO.

Geometry only: generated perimeter surfaces are not sourced wall constructions.
Run separately from production simulation; no templates or regulations applied.
"""
import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys

from probe_moosas_ifc import PIN


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_space_envelopes(model, audit):
    """Compare each saved space's boundary ownership against independent IFC facts."""
    from shapely import get_coordinates
    actual = {s.id:s for s in model.spaceList}
    details = []
    for source in audit['spaces']:
        guid = source['guid']; space = actual.get(guid)
        row = dict(guid=guid, boundary_ownership_preserved=False)
        if space is not None and space.floor is not None and space.ceiling is not None:
            x,y,z = source['origin_m']; w,d,h = source['size_m']
            points = [(x,y,z),(x+w,y,z),(x+w,y+d,z),(x,y+d,z),
                      (x,y,z+h),(x+w,y,z+h),(x+w,y+d,z+h),(x,y+d,z+h)]
            indices = ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
            def vertices(values):
                return sorted(set(tuple(round(float(n),9) for n in p) for p in values))
            expected = {guid+'_'+str(i):vertices([points[j] for j in face]) for i,face in enumerate(indices)}
            surfaces = list(space.floor.face)+list(space.ceiling.face)+list(space.edge.wall)
            found = {str(s.Uid):vertices(get_coordinates(s.face,include_z=True)) for s in surfaces}
            row['boundary_ownership_preserved'] = (
                len(space.floor.face)==1 and len(space.ceiling.face)==1 and len(space.edge.wall)==4
                and str(space.floor.face[0].Uid)==guid+'_0' and str(space.ceiling.face[0].Uid)==guid+'_1'
                and len(found)==len(surfaces)==6 and found==expected)
        details.append(row)
    return details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('ifc', 'binding', 'upstream', 'deps', 'out'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = {k: v.resolve() for k, v in vars(args).items()}
    if not all(p.is_relative_to(root) for p in paths.values()) or paths['out'].exists():
        parser.error('Use repository-local paths and a new output directory')
    checkout = paths['upstream']
    if subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip() != PIN:
        parser.error('Upstream commit differs')
    if subprocess.check_output(['git','-C',str(checkout),'status','--porcelain'],text=True).strip():
        parser.error('Upstream checkout must be clean')
    inputs = {str(paths[k]): digest(paths[k]) for k in ('ifc','binding')}
    sys.path[:0] = [str(checkout), str(paths['deps'])]
    from importlib.metadata import version
    dependency_versions = {name: version(name) for name in ('rdflib','pyparsing')}
    if dependency_versions != {'rdflib':'7.1.4','pyparsing':'3.2.3'}:
        parser.error('Expected isolated rdflib 7.1.4 and pyparsing 3.2.3')
    from bsa.thermal_binding import extract
    from MoosasPy.model import MoosasModel, MoosasSpace, MoosasFloor, MoosasEdge
    from MoosasPy.transform.geometry.element import MoosasFace, MoosasWall
    from shapely.geometry import Polygon
    from shapely import get_coordinates
    binding = json.loads(paths['binding'].read_text(encoding='utf-8-sig'))
    rows, audit = extract(paths['ifc'], binding)
    if not rows:
        parser.error('At least one source-verified box space is required')
    model = MoosasModel()
    model.levelList = sorted({r['origin_m'][2]+v*r['size_m'][2] for r in rows for v in (0,1)})
    for row, basis in zip(rows, binding['spaces']):
        x,y,z = row['origin_m']; w,d,h = row['size_m']
        points = [(x,y,z),(x+w,y,z),(x+w,y+d,z),(x,y+d,z),
                  (x,y,z+h),(x+w,y,z+h),(x+w,y+d,z+h),(x,y+d,z+h)]
        surfaces = []
        for i, indices in enumerate(((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))):
            geo = model.includeGeo(Polygon([points[n] for n in indices]))
            kind = MoosasFace if i < 2 else MoosasWall
            obj = kind(model, geo, level=z+h if i == 1 else z, offset=0, uid=basis['guid']+'_'+str(i))
            surfaces.append(obj)
            (model.faceList if i < 2 else model.wallList).append(obj)
        space = MoosasSpace(MoosasFloor([surfaces[0]]),
            MoosasEdge(surfaces[2:], boundary=Polygon(points[:4])),
            MoosasFloor([surfaces[1]]), Uid=basis['guid'])
        model.spaceList.append(space)
    out = paths['out']; out.mkdir(parents=True)
    model.save(out/'envelopes.xml')
    catalog = out/'geometry-only-catalog'; catalog.mkdir()
    (catalog/'library.json').write_text(json.dumps(dict(schema='moosas.building-template-library',version=5,standards=[])))
    templates = importlib.import_module('MoosasPy.model.building_templates')
    previous = templates.DEFAULT_LIBRARY
    try:
        templates.DEFAULT_LIBRARY = catalog
        loaded = MoosasModel.load(out/'envelopes.xml')
    finally:
        templates.DEFAULT_LIBRARY = previous
    def vertices(m):
        return sorted([sorted(set(tuple(round(float(n),9) for n in p) for p in get_coordinates(g.face,include_z=True))) for g in m.geometryList])
    actual = {s.id:s for s in loaded.spaceList}
    boundary_checks = check_space_envelopes(loaded, audit)
    checks = dict(space_identity_preserved=len(actual)==len(rows)==len(loaded.spaceList)
                  and set(actual)=={b['guid'] for b in binding['spaces']},
                  per_space_boundaries_preserved=all(r['boundary_ownership_preserved'] for r in boundary_checks),
                  face_vertices_preserved=vertices(model)==vertices(loaded),
                  dimensions_preserved=all(e['guid'] in actual
                    and math.isclose(actual[e['guid']].area,e['floor_area_m2'],abs_tol=1e-8)
                    and math.isclose(actual[e['guid']].height,e['size_m'][2],abs_tol=1e-8)
                    and not actual[e['guid']].is_open() for e in audit['spaces']),
                  inputs_unchanged=all(digest(Path(p))==sha for p,sha in inputs.items()))
    result = dict(upstream_commit=PIN,dependencies=dependency_versions,inputs=inputs,geometry=audit,checks=checks,boundary_checks=boundary_checks,
                  geometry_exchange_pass=all(checks.values()),simulation_executed=False,design_accepted=False,
                  scope='Box-space envelopes only; material, shared boundaries, thermal settings, system topology and regulatory acceptance unresolved',
                  compatibility='Explicit empty version-5 catalogue; no template applied',
                  artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()})
    (out/'exchange.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(checks))
    return 0 if result['geometry_exchange_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
