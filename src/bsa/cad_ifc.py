"""Source-bound native CAD solid to an unconnected tessellated IFC fitting."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import re
import shutil
import struct
import numpy as np
from .cad_intake import export_dwg, METRES_PER_UNIT
from .cli import digest
from .engine import ProjectError
from .native_cad import DEFAULT_EXE, execute, lisp_string
from .solid_clash import from_mesh
from .tee_geometry import project_namespace, stable_guid


def mass_properties(text):
    n = r'([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)'
    volumes = re.findall(r'Volume:\s*' + n, text)
    bounds = re.findall(r'([XYZ]):\s*' + n + r'\s*--\s*' + n, text)
    centres = re.findall(r'Centroid:\s*X:\s*' + n + r'\s*Y:\s*' + n + r'\s*Z:\s*' + n, text)
    if len(volumes) != 1 or len(bounds) != 3 or [b[0] for b in bounds] != list('XYZ') or len(centres) != 1:
        raise ProjectError('unambiguous native mass properties required')
    result = {'volume': float(volumes[0]), 'bounds': np.array([[float(b[1]), float(b[2])] for b in bounds]).T,
              'centroid': np.array([float(x) for x in centres[0]])}
    if (not math.isfinite(result['volume']) or result['volume'] <= 0
            or not np.isfinite(result['bounds']).all() or not np.isfinite(result['centroid']).all()
            or not np.all(result['bounds'][1] > result['bounds'][0])):
        raise ProjectError('finite positive native solid properties required')
    return result


def mesh_properties(vertices, faces):
    v, f = np.array(vertices, dtype=float, copy=True), np.array(faces, dtype=np.int64, copy=True)
    solid = from_mesh((v, f))
    if len(solid.decompose()) != 1:
        raise ProjectError('one connected closed wall required')
    origin = (v.min(axis=0)+v.max(axis=0))/2
    triangles = v[f]-origin
    signed = np.einsum('ij,ij->i', triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])) / 6
    volume = signed.sum()
    if volume <= 0 or not math.isfinite(volume):
        raise ProjectError('positive oriented mesh volume required')
    centroid = np.sum(triangles.sum(axis=1) * signed[:, None] / 4, axis=0) / volume + origin
    return {'volume': float(volume), 'bounds': np.array([v.min(axis=0), v.max(axis=0)]), 'centroid': centroid}


def compare(actual, reference, linear, relative_volume):
    return {'volume': math.isclose(actual['volume'], reference['volume'], rel_tol=relative_volume, abs_tol=0),
            'bounds': bool(np.allclose(actual['bounds'], reference['bounds'], atol=linear, rtol=0)),
            'centroid': bool(np.allclose(actual['centroid'], reference['centroid'], atol=linear, rtol=0))}


def run(source, basis_path, out, exe=DEFAULT_EXE, timeout=120):
    import ezdxf
    from ezdxf.addons import meshex
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.geom
    import ifcopenshell.util.shape
    source, basis_path, out, exe = [Path(x).resolve() for x in (source, basis_path, out, exe)]
    b = json.loads(basis_path.read_text(encoding='utf-8-sig'))
    required = {'source', 'drawing_sha256', 'solid_handle', 'insunits', 'project_uuid', 'id',
                'linear_tolerance_m', 'relative_volume_tolerance'}
    if not isinstance(b, dict) or set(b) != required:
        raise ProjectError('exact native IFC conversion basis required')
    project_namespace(b)
    for k in ('source', 'id', 'solid_handle', 'drawing_sha256'):
        if not isinstance(b[k], str) or not b[k].strip(): raise ProjectError('source and identity required')
    if not re.fullmatch('[0-9A-Fa-f]+', b['solid_handle']): raise ProjectError('hexadecimal solid handle required')
    if type(b['insunits']) is not int or b['insunits'] not in METRES_PER_UNIT:
        raise ProjectError('explicit supported units required')
    for k in ('linear_tolerance_m', 'relative_volume_tolerance'):
        if type(b[k]) not in (int, float) or not math.isfinite(b[k]) or b[k] <= 0:
            raise ProjectError('positive finite numerical comparison tolerances required')
    versions = {k: importlib.metadata.version(k) for k in ('ifcopenshell', 'manifold3d', 'ezdxf')}
    if versions != {'ifcopenshell': '0.8.5', 'manifold3d': '3.5.4', 'ezdxf': '1.4.5'}:
        raise ProjectError('verified pinned geometry runtimes required')
    before = {str(p): digest(p) for p in (source, basis_path)}
    if before[str(source)] != b['drawing_sha256']: raise ProjectError('source hash mismatch')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out == p or out in p.parents for p in (source, basis_path)):
        raise ProjectError('new repository output outside inputs required')
    out.mkdir(parents=True)
    exported = export_dwg(source, out/'intake', exe, timeout)
    doc = ezdxf.readfile(exported); audit = doc.audit(); solids = list(doc.modelspace().query('3DSOLID'))
    if audit.errors or audit.fixes or doc.units != b['insunits'] or len(solids) != 1 or solids[0].dxf.handle.upper() != b['solid_handle'].upper():
        raise ProjectError('one selected solid in clean source with matching units required')
    copied = out/'source-copy.dwg'; shutil.copyfile(source, copied)
    guard = f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))'
    setup = ('(setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (setvar "OSMODE" 0) '
             '(setvar "LUPREC" 8) (setvar "LUNITS" 2) (command "_.UCS" "_World") '
             f'(setq solid (handent {lisp_string(b["solid_handle"])})) ')
    def native(name, body):
        script = out/(name+'.scr')
        script.write_text(f'(if {guard} (progn {setup} {body}) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n', encoding='ascii')
        execute(exe, copied, script, out/(name+'.log'), timeout)
        if digest(copied) != before[str(source)]: raise ProjectError('native source copy changed')
    native('mass', f'(command "_.MASSPROP" solid "" "_Y" {lisp_string(out/"solid.mpr")})')
    props = mass_properties((out/'solid.mpr').read_text())
    # Explicitly move to positive coordinates to avoid STLOUT's implicit relocation.
    # The inverse is recorded and applied after export; all three statistics verify it.
    shift = 1 - props['bounds'][0]
    shift_text = ','.join(format(x, '.17g') for x in shift)
    native('stl', f'(setvar "FACETRES" 10) (command "_.MOVE" solid "" "0,0,0" {lisp_string(shift_text)}) '
           f'(command "_.STLOUT" solid "" "_Y" {lisp_string(out/"solid.stl")})')
    raw = (out/'solid.stl').read_bytes()
    if len(raw) < 84 or len(raw) != 84 + 50*struct.unpack_from('<I', raw, 80)[0]:
        raise ProjectError('exact binary STL length required')
    mesh = meshex.stl_loadb(raw); scale = METRES_PER_UNIT[b['insunits']]
    vertices = (np.asarray(mesh.vertices)-shift)*scale; faces = np.asarray(mesh.faces, dtype=np.int64)
    reference = {'volume': props['volume']*scale**3, 'bounds': props['bounds']*scale, 'centroid': props['centroid']*scale}
    measured = mesh_properties(vertices, faces)
    stl_checks = compare(measured, reference, b['linear_tolerance_m'], b['relative_volume_tolerance'])
    if not all(stl_checks.values()): raise ProjectError(f'native/STL reconciliation failed: {stl_checks}')
    f = ifcopenshell.file(schema='IFC4')
    project = api.run('root.create_entity', f, ifc_class='IfcProject', name='Source CAD fitting conversion')
    unit = api.run('unit.add_si_unit', f, unit_type='LENGTHUNIT'); api.run('unit.assign_unit', f, units=[unit])
    model = api.run('context.add_context', f, context_type='Model')
    context = api.run('context.add_context', f, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW', parent=model)
    storey = api.run('root.create_entity', f, ifc_class='IfcBuildingStorey', name='Local source definition')
    api.run('aggregate.assign_object', f, products=[storey], relating_object=project)
    obj = api.run('root.create_entity', f, ifc_class='IfcPipeFitting', predefined_type='JUNCTION', name=b['id'])
    obj.GlobalId = stable_guid(b, 'IfcPipeFitting', b['id'])
    api.run('spatial.assign_container', f, products=[obj], relating_structure=storey)
    points = f.createIfcCartesianPointList3D(vertices.tolist())
    tess = f.createIfcTriangulatedFaceSet(Coordinates=points, Closed=True, CoordIndex=(faces+1).tolist())
    rep = f.createIfcShapeRepresentation(context, 'Body', 'Tessellation', [tess])
    api.run('geometry.assign_representation', f, product=obj, representation=rep)
    api.run('geometry.edit_object_placement', f, product=obj, matrix=np.eye(4), is_si=True)
    ps = api.run('pset.add_pset', f, product=obj, name='BSA_CADSource')
    api.run('pset.edit_pset', f, pset=ps, properties={'Source': b['source'], 'DrawingSHA256': b['drawing_sha256'],
        'SolidHandle': b['solid_handle'], 'Scope': 'Unconnected tessellated source body; no product/hydraulic acceptance'})
    path = out/'fitting.ifc'; f.write(str(path)); saved = ifcopenshell.open(str(path))
    shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), saved.by_guid(obj.GlobalId))
    sv = ifcopenshell.util.shape.get_vertices(shape.geometry); sf = ifcopenshell.util.shape.get_faces(shape.geometry)
    saved_props = mesh_properties(sv, sf)
    saved_checks = compare(saved_props, measured, 1e-9, 1e-9)
    saved_tess = saved.by_guid(obj.GlobalId).Representation.Representations[0].Items[0]
    saved_checks['source_triangles_preserved'] = (
        saved_tess.is_a('IfcTriangulatedFaceSet') and saved_tess.Closed is True
        and np.array_equal(np.asarray(saved_tess.CoordIndex), faces+1)
        and np.allclose(np.asarray(saved_tess.Coordinates.CoordList), vertices, atol=1e-12, rtol=0))
    if not all(saved_checks.values()): raise ProjectError(f'saved IFC mesh reconciliation failed: {saved_checks}')
    if any(digest(Path(p)) != h for p, h in before.items()): raise ProjectError('conversion input changed')
    serial = lambda p: {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in p.items()}
    result = {'inputs': before, 'basis': b, 'runtime': versions, 'guid': obj.GlobalId,
              'native_properties_si': serial(reference), 'stl_properties_si': serial(measured),
              'saved_ifc_properties_si': serial(saved_props), 'export_translation_drawing_units': shift.tolist(),
              'vertices': len(vertices), 'triangles': len(faces), 'stl_checks': stl_checks, 'saved_ifc_checks': saved_checks,
              'geometry_conversion_pass': True, 'design_accepted': False,
              'pending': ['ports/system/project placement', 'saved IFC bore and clash checks', 'viewer review',
                          'product/hydraulic/regulatory acceptance'],
              'artifacts': {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('*') if p.is_file()}}
    (out/'cad-ifc.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('source'); p.add_argument('basis')
    p.add_argument('--out', required=True); p.add_argument('--autocad', default=str(DEFAULT_EXE))
    a = p.parse_args(); r = run(a.source, a.basis, a.out, a.autocad)
    print(json.dumps({k: r[k] for k in ('guid', 'triangles', 'stl_checks', 'saved_ifc_checks', 'design_accepted')}))
