"""Measure explicitly located circular annular sections of a native CAD solid."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil

from .cad_intake import export_dwg, METRES_PER_UNIT
from .cli import digest
from .engine import ProjectError
from .native_cad import DEFAULT_EXE, execute, lisp_string

NORMALS = {'XY': (0, 0, 1), 'YZ': (1, 0, 0), 'ZX': (0, 1, 0)}


def validate(basis):
    required = {'source', 'drawing_sha256', 'solid_handle', 'insunits', 'tolerance_m', 'sections'}
    if not isinstance(basis, dict) or set(basis) != required:
        raise ProjectError('exact section basis required')
    for key in ('source', 'drawing_sha256', 'solid_handle'):
        if not isinstance(basis[key], str) or not basis[key].strip():
            raise ProjectError('source and solid identity required')
    if not re.fullmatch(r'[0-9a-f]{64}', basis['drawing_sha256']):
        raise ProjectError('SHA256 required')
    if not re.fullmatch(r'[0-9A-Fa-f]+', basis['solid_handle']):
        raise ProjectError('hexadecimal solid handle required')
    if type(basis['insunits']) is not int or basis['insunits'] not in METRES_PER_UNIT:
        raise ProjectError('explicit supported units required')
    tolerance = basis['tolerance_m']
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ProjectError('positive finite length tolerance required')
    if not isinstance(basis['sections'], list) or not basis['sections']:
        raise ProjectError('explicit section locations required')
    seen = set()
    for row in basis['sections']:
        if not isinstance(row, dict) or set(row) != {'id', 'source', 'plane', 'centre_drawing_units'}:
            raise ProjectError('exact section fields required')
        if not isinstance(row['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]+', row['id']) or row['id'] in seen:
            raise ProjectError('unique safe section IDs required')
        seen.add(row['id'])
        if (not isinstance(row['source'], str) or not row['source'].strip()
                or not isinstance(row['plane'], str) or row['plane'] not in NORMALS):
            raise ProjectError('section source and supported plane required')
        point = row['centre_drawing_units']
        if not isinstance(point, list) or len(point) != 3 or any(
            type(x) not in (int, float) or not math.isfinite(x) for x in point
        ):
            raise ProjectError('finite three-coordinate section centre required')


def boundary_inventory(doc, row, insunits):
    """Report native section primitives without inferring which boundary is a bore."""
    from collections import Counter
    if doc.units != insunits:
        raise ProjectError('section export units mismatch')
    entities = [e for e in doc.modelspace() if e.dxf.layer == 'BSA_SECTION_' + row['id']]
    scale = METRES_PER_UNIT[insunits]
    circles = []
    for e in entities:
        if e.dxftype() == 'CIRCLE':
            circles.append({'handle': e.dxf.handle,
                            'centre_m': [float(x)*scale for x in e.ocs().to_wcs(e.dxf.center)],
                            'radius_m': float(e.dxf.radius)*scale,
                            'normal': list(e.dxf.extrusion)})
    return {'entity_counts': dict(Counter(e.dxftype() for e in entities)),
            'circles': circles, 'scope': 'Primitive inventory only; no boundary role or annular acceptance'}


def measure(doc, row, insunits, tolerance_m):
    if doc.units != insunits:
        raise ProjectError('section export units mismatch')
    layer = 'BSA_SECTION_' + row['id']
    entities = [e for e in doc.modelspace() if e.dxf.layer == layer]
    if len(entities) != 2 or any(e.dxftype() != 'CIRCLE' for e in entities):
        raise ProjectError('section must contain exactly two circular boundaries')
    scale = METRES_PER_UNIT[insunits]
    normal = NORMALS[row['plane']]
    centres, radii = [], []
    for entity in entities:
        centre = list(entity.ocs().to_wcs(entity.dxf.center))
        radius = entity.dxf.radius * scale
        axis = list(entity.dxf.extrusion)
        if not all(math.isfinite(x) for x in centre + axis + [radius]) or radius <= 0:
            raise ProjectError('invalid section geometry')
        if abs(math.sqrt(sum(x*x for x in axis)) - 1) > 1e-9 or abs(abs(sum(a*b for a, b in zip(axis, normal))) - 1) > 1e-9:
            raise ProjectError('circle normal does not match section plane')
        if math.dist(centre, row['centre_drawing_units']) * scale > tolerance_m:
            raise ProjectError('section centre does not match source location')
        centres.append(centre); radii.append(radius)
    if math.dist(*centres) * scale > tolerance_m:
        raise ProjectError('section circles are not concentric')
    inner, outer = sorted(radii)
    if outer - inner <= tolerance_m:
        raise ProjectError('resolvable annular wall required')
    return {'id': row['id'], 'source': row['source'], 'plane': row['plane'],
            'centre_m': [x * scale for x in row['centre_drawing_units']],
            'inner_diameter_m': 2 * inner, 'outer_diameter_m': 2 * outer,
            'wall_thickness_m': outer - inner,
            'boundary_handles': [e.dxf.handle for e in entities]}


def run(source, basis_path, out, exe=DEFAULT_EXE, timeout=120):
    import ezdxf
    source, basis_path, out, exe = [Path(p).resolve() for p in (source, basis_path, out, exe)]
    basis = json.loads(basis_path.read_text(encoding='utf-8-sig')); validate(basis)
    before = {str(p): digest(p) for p in (source, basis_path)}
    if before[str(source)] != basis['drawing_sha256']:
        raise ProjectError('section source hash mismatch')
    if (out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2])
            or any(out == p or out in p.parents for p in (source, basis_path))):
        raise ProjectError('new repository output outside inputs required')
    out.mkdir(parents=True)
    exported = export_dwg(source, out / 'source-intake', exe, timeout)
    doc = ezdxf.readfile(exported); audit = doc.audit()
    if audit.errors or audit.fixes or doc.units != basis['insunits']:
        raise ProjectError('source export audit or units failed')
    solid = doc.entitydb.get(basis['solid_handle'])
    if solid is None or solid.dxftype() != '3DSOLID' or solid not in doc.modelspace():
        raise ProjectError('selected model-space solid missing')
    for row in basis['sections']:
        if 'BSA_SECTION_' + row['id'] in doc.layers:
            raise ProjectError('reserved diagnostic layer already exists')
    results = []
    for row in basis['sections']:
        folder = out / row['id']; folder.mkdir()
        copied = folder / 'source-copy.dwg'; shutil.copyfile(source, copied)
        target = folder / 'section.dxf'; script = folder / 'section.scr'
        layer = 'BSA_SECTION_' + row['id']
        point = ','.join(format(x, '.17g') for x in row['centre_drawing_units'])
        guard = (f'(= (strcase (vl-string-translate (chr 92) "/" '
                 f'(strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))')
        # Gather every newly generated region. No-hit/multiple-region results cannot
        # accidentally explode the previous entity or produce an accepted export.
        body = (f'(setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (setvar "OSMODE" 0) '
                f'(command "_.UCS" "_World") (setq solid (handent {lisp_string(basis["solid_handle"])})) '
                '(if (and solid (= (cdr (assoc 0 (entget solid))) "3DSOLID")) (progn '
                '(setq old (entlast)) '
                f'(command "_.SECTION" solid "" {lisp_string("_" + row["plane"])} {lisp_string(point)}) '
                '(setq e (entnext old) regions nil) '
                '(while e (setq regions (cons e regions) e (entnext e))) '
                '(if (and (= (length regions) 1) (= (cdr (assoc 0 (entget (car regions)))) "REGION")) (progn '
                f'(command "_.-LAYER" "_New" {lisp_string(layer)} "") '
                f'(entmod (subst (cons 8 {lisp_string(layer)}) (assoc 8 (entget (car regions))) (entget (car regions)))) '
                '(command "_.EXPLODE" (car regions) "") '
                f'(command "_.DXFOUT" {lisp_string(target)} "16")) (princ "BSA SECTION NOT SINGLE REGION"))) '
                '(princ "BSA SOLID MISSING"))')
        script.write_text(f'(if {guard} (progn {body}) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n', encoding='ascii')
        execute(exe, copied, script, folder / 'section.log', timeout)
        if not target.is_file():
            raise ProjectError(f'section {row["id"]} did not produce a single region')
        section = ezdxf.readfile(target); audit = section.audit()
        if audit.errors or audit.fixes:
            raise ProjectError('section export requires repair')
        inventory = boundary_inventory(section, row, basis['insunits'])
        inventory.update(dxf_sha256=digest(target), source_sha256=before[str(source)], section=row)
        (folder / 'boundary-inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
        result = measure(section, row, basis['insunits'], basis['tolerance_m'])
        result['dxf_sha256'] = digest(target); results.append(result)
        if digest(copied) != before[str(source)]:
            raise ProjectError('source copy changed on disk')
    if any(digest(Path(p)) != h for p, h in before.items()):
        raise ProjectError('section input changed')
    result = {'inputs': before, 'basis': basis, 'sections': results, 'annular_sections_pass': True,
              'design_accepted': False, 'scope': 'Sampled planar model geometry only; not a product bore specification',
              'pending': ['interior connectivity and minimum passage', 'port frame and joint compatibility',
                          'manufacturer dimensional confirmation', 'hydraulic and regulatory applicability'],
              'artifacts': {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('*') if p.is_file()}}
    (out / 'sections.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source'); p.add_argument('basis'); p.add_argument('--out', required=True)
    p.add_argument('--autocad', default=str(DEFAULT_EXE))
    a = p.parse_args(); result = run(a.source, a.basis, a.out, a.autocad)
    print(json.dumps({'sections': result['sections'], 'design_accepted': False}, indent=2))
