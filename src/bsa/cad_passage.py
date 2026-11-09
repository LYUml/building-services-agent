"""Native solid/cylindrical-probe intersections; bounded clearance, not hydraulic acceptance."""
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


def validate(b):
    if not isinstance(b, dict) or set(b) != {'source', 'drawing_sha256', 'solid_handle', 'insunits', 'probes'}:
        raise ProjectError('exact passage basis required')
    if not isinstance(b['source'], str) or not b['source'].strip():
        raise ProjectError('passage basis source required')
    if not isinstance(b['drawing_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', b['drawing_sha256']):
        raise ProjectError('source SHA256 required')
    if not isinstance(b['solid_handle'], str) or not re.fullmatch('[0-9A-Fa-f]+', b['solid_handle']):
        raise ProjectError('solid handle required')
    if type(b['insunits']) is not int or b['insunits'] not in METRES_PER_UNIT:
        raise ProjectError('supported units required')
    if not isinstance(b['probes'], list) or not b['probes']:
        raise ProjectError('passage and wall-control probes required')
    ids, roles = set(), set()
    for p in b['probes']:
        if not isinstance(p, dict) or set(p) != {'id', 'source', 'role', 'start', 'end', 'radius'}:
            raise ProjectError('exact probe fields required')
        if not isinstance(p['id'], str) or not re.fullmatch('[A-Za-z0-9_-]+', p['id']) or p['id'] in ids:
            raise ProjectError('unique safe probe IDs required')
        ids.add(p['id'])
        if p['role'] not in ('passage', 'wall_control') or not isinstance(p['source'], str) or not p['source'].strip():
            raise ProjectError('probe role and source required')
        roles.add(p['role'])
        for key in ('start', 'end'):
            if not isinstance(p[key], list) or len(p[key]) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in p[key]):
                raise ProjectError('finite three-coordinate probe endpoints required')
        length = math.dist(p['start'], p['end'])
        if type(p['radius']) not in (int, float) or not math.isfinite(p['radius']) or p['radius'] <= 0 or not math.isfinite(length) or length <= 0:
            raise ProjectError('positive finite radius and cylinder length required')
    if roles != {'passage', 'wall_control'}:
        raise ProjectError('both passage and positive wall control required')


def check_probe(text, p):
    """Check native mass properties against independently calculated cylinder geometry."""
    number = r'([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)'
    volumes = re.findall(r'Volume:\s*' + number, text)
    bounds = re.findall(r'(?:Bounding box:\s*)?([XYZ]):\s*' + number + r'\s*--\s*' + number, text)
    if len(volumes) != 1 or len(bounds) != 3 or {x[0] for x in bounds} != {'X', 'Y', 'Z'}:
        raise ProjectError('native cylinder mass properties missing or ambiguous')
    length = math.dist(p['start'], p['end']); radius = p['radius']
    expected_volume = math.pi * radius * radius * length
    actual_volume = float(volumes[0])
    if (not math.isfinite(expected_volume) or expected_volume <= 1e-7 or not math.isfinite(actual_volume)
            or actual_volume <= 0 or not math.isclose(actual_volume, expected_volume, rel_tol=1e-7, abs_tol=1e-7)):
        raise ProjectError('native probe volume differs from specified cylinder')
    unit = [(y-x)/length for x, y in zip(p['start'], p['end'])]
    observed = {axis: (float(lo), float(hi)) for axis, lo, hi in bounds}
    for i, axis in enumerate('XYZ'):
        margin = radius * math.sqrt(max(0, 1-unit[i]**2))
        expected = (min(p['start'][i], p['end'][i])-margin, max(p['start'][i], p['end'][i])+margin)
        if any(not math.isclose(a, e, rel_tol=0, abs_tol=1e-7) for a, e in zip(observed[axis], expected)):
            raise ProjectError('native probe bounds differ from specified cylinder')
    return {'volume_drawing_units3': actual_volume, 'bounds_drawing_units': observed}


def run(source, basis_path, out, exe=DEFAULT_EXE, timeout=120):
    import ezdxf
    source, basis_path, out, exe = [Path(x).resolve() for x in (source, basis_path, out, exe)]
    b = json.loads(basis_path.read_text(encoding='utf-8-sig')); validate(b)
    before = {str(p): digest(p) for p in (source, basis_path)}
    if before[str(source)] != b['drawing_sha256']:
        raise ProjectError('passage source hash mismatch')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out == p or out in p.parents for p in (source, basis_path)):
        raise ProjectError('new repository output outside inputs required')
    out.mkdir(parents=True)
    exported = export_dwg(source, out/'source-intake', exe, timeout)
    doc = ezdxf.readfile(exported); audit = doc.audit()
    solids = list(doc.modelspace().query('3DSOLID'))
    if audit.errors or audit.fixes or doc.units != b['insunits'] or len(solids) != 1 or solids[0].dxf.handle.upper() != b['solid_handle'].upper():
        raise ProjectError('exact selected single solid, clean source and matching units required')
    rows = []
    for p in b['probes']:
        folder = out/p['id']; folder.mkdir(); copied = folder/'copy.dwg'; shutil.copyfile(source, copied)
        target = folder/'intersection.dxf'; mpr = folder/'probe.mpr'; initial = folder/'before.dxf'
        point = lambda key: lisp_string(','.join(format(x, '.17g') for x in p[key]))
        guard = f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(copied)}))'
        body = ('(setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (setvar "OSMODE" 0) (setvar "LUPREC" 8) '
                '(setvar "LUNITS" 2) (command "_.UCS" "_World") '
                f'(setq solid (handent {lisp_string(b["solid_handle"])})) '
                '(if (and solid (= (cdr (assoc 0 (entget solid))) "3DSOLID")) (progn '
                f'(command "_.CYLINDER" {point("start")} {lisp_string(format(p["radius"], ".17g"))} "_A" {point("end")}) '
                '(setq probe (entlast)) '
                '(if (and (/= probe solid) (= (cdr (assoc 0 (entget probe))) "3DSOLID")) (progn '
                f'(command "_.MASSPROP" probe "" "_Y" {lisp_string(mpr)}) '
                f'(command "_.DXFOUT" {lisp_string(initial)} "16") '
                '(command "_.INTERSECT" solid probe "") '
                f'(command "_.DXFOUT" {lisp_string(target)} "16")) (princ "BSA PROBE MISSING"))) '
                '(princ "BSA SOLID MISSING"))')
        script = folder/'probe.scr'
        script.write_text(f'(if {guard} (progn {body}) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n', encoding='ascii')
        execute(exe, copied, script, folder/'probe.log', timeout)
        if not all(x.is_file() for x in (mpr, initial, target)):
            raise ProjectError('native probe evidence incomplete')
        measured = check_probe(mpr.read_text(), p)
        documents = [ezdxf.readfile(x) for x in (initial, target)]
        for d in documents:
            a = d.audit()
            if a.errors or a.fixes or d.units != b['insunits']:
                raise ProjectError('probe native export audit or units failed')
        counts = [len(list(d.modelspace().query('3DSOLID'))) for d in documents]
        if counts[0] != 2 or counts[1] not in (0, 1):
            raise ProjectError('unexpected native Boolean solid counts')
        if digest(copied) != before[str(source)]:
            raise ProjectError('probe source copy changed on disk')
        clear = counts[1] == 0
        rows.append({'id': p['id'], 'role': p['role'], 'probe_check': measured,
                     'intersection_solid_count': counts[1], 'clear': clear,
                     'expectation_pass': clear == (p['role'] == 'passage')})
    if any(digest(Path(p)) != h for p, h in before.items()):
        raise ProjectError('passage source changed during run')
    result = {'inputs': before, 'basis': b, 'probes': rows,
              'passage_checks_pass': all(r['expectation_pass'] for r in rows), 'design_accepted': False,
              'scope': 'Specified cylindrical probe clearance with positive wall control; native kernel tolerance applies',
              'pending': ['probe-to-port/topology applicability', 'minimum bore and all interior geometry',
                          'manufacturer dimensional guarantees', 'hydraulic and regulatory applicability'],
              'artifacts': {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('*') if p.is_file()}}
    (out/'passage.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('basis'); parser.add_argument('--out', required=True)
    parser.add_argument('--autocad', default=str(DEFAULT_EXE))
    a = parser.parse_args(); r = run(a.source, a.basis, a.out, a.autocad)
    print(json.dumps({'probes': r['probes'], 'passage_checks_pass': r['passage_checks_pass']}, indent=2))
    raise SystemExit(0 if r['passage_checks_pass'] else 2)
