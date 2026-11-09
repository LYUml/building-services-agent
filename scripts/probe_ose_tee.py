"""Run with portable FreeCAD's Python: source checkout, dimensions JSON, new output.

Compatibility/geometry trial only. Calls unmodified OSE Piping; no IFC acceptance.
"""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

PIN = '690ab65511be2cdbe8ce292cb59e5335d157ac09'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    upstream, source, out = (Path(x).resolve() for x in sys.argv[1:])
    assert subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == PIN
    assert not subprocess.check_output(['git', '-C', str(upstream), 'status', '--porcelain'], text=True).strip()
    assert out != source and out not in source.parents and out != upstream and upstream not in out.parents and out not in upstream.parents
    data = json.loads(source.read_text(encoding='utf-8'))
    assert data['kind'] == 'synthetic compatibility trial' and data['source']
    values = data['dimensions_mm']
    names = {n+s for n in ('G', 'H', 'M', 'POD', 'PThk') for s in ('', '1', '2')}
    assert set(values) == names
    assert all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in values.values())
    # First trial deliberately limited to equal three-way socket dimensions.
    assert all(values[n] == values[n+'1'] == values[n+'2'] for n in ('G', 'H', 'M', 'POD', 'PThk'))
    assert 0 < values['PThk'] < values['POD']/2 < values['M']/2 < values['G'] < values['H']
    before = sha(source)
    sys.path.insert(0, str(upstream))
    import FreeCAD as App
    import Part
    from OsePiping.Tee import Tee
    out.mkdir(parents=True, exist_ok=False)
    doc = App.newDocument('BSASyntheticTeeProbe')
    tee = Tee(doc)
    for name, value in values.items():
        setattr(tee.dims, name, App.Units.parseQuantity(str(value)+' mm'))
    part = tee.create(False)
    doc.recompute()
    shape = part.Shape
    h, g = values['H'], values['G']
    outer, inner = values['POD']/2, values['POD']/2-values['PThk']
    vec = App.Vector
    bore = Part.makeCylinder(inner-0.01, 2*h, vec(-h, 0, 0), vec(1, 0, 0)).fuse(
        Part.makeCylinder(inner-0.01, h, vec(0, 0, 0), vec(0, 0, 1)))
    # Explicit fixture pipes extend from the internal socket shoulders outwards.
    interfaces = [([-g, 0, 0], [-1, 0, 0]), ([g, 0, 0], [1, 0, 0]), ([0, 0, g], [0, 0, 1])]
    overlaps = []
    for point, direction in interfaces:
        pipe = Part.makeCylinder(outer, h-g+200, vec(*point), vec(*direction)).cut(
            Part.makeCylinder(inner, h-g+200, vec(*point), vec(*direction)))
        overlaps.append(shape.common(pipe).Volume)
    # Deliberately translate a valid connection sideways: must detect material penetration.
    bad = Part.makeCylinder(outer, h-g+200, vec(g, 2, 0), vec(1, 0, 0)).cut(
        Part.makeCylinder(inner, h-g+200, vec(g, 2, 0), vec(1, 0, 0)))
    bad_overlap = shape.common(bad).Volume
    path = out/'tee.FCStd'
    doc.saveAs(str(path))
    shape.exportBrep(str(out/'tee.brep'))
    Part.export([part], str(out/'tee.step'))
    original_volume = shape.Volume
    part_name = part.Name
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(path))
    saved = reopened.getObject(part_name).Shape
    brep = Part.Shape(); brep.read(str(out/'tee.brep'))
    checks = dict(valid_solid=saved.isValid() and len(saved.Solids) == 1 and saved.Volume > 0,
                  saved_volume_matches=abs(saved.Volume-original_volume) < 1e-6,
                  brep_matches=brep.isValid() and abs(brep.Volume-original_volume) < 1e-6,
                  open_bore=saved.common(bore).Volume < 1e-6,
                  socket_pipes_no_material_overlap=all(v < 1e-6 for v in overlaps),
                  displaced_pipe_detected=bad_overlap > 1,
                  source_unchanged=sha(source) == before)
    result = dict(upstream_commit=PIN, freecad_version=App.Version(), source_sha256=before,
                  upstream_files={n: sha(upstream/n) for n in ('OsePiping/Tee.py', 'OsePiping/Piping.py', 'OsePipingBase.py', 'LICENSE', 'README.md')},
                  volume_mm3=saved.Volume, socket_overlap_mm3=overlaps, displaced_pipe_overlap_mm3=bad_overlap,
                  connection_shoulders_mm=interfaces, checks=checks, trial_pass=all(checks.values()),
                  design_accepted=False, scope='Equal synthetic socket tee only; no product, IFC, hydraulic or regulatory acceptance')
    App.closeDocument(reopened.Name)
    result['artifacts'] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    (out/'probe.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['trial_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
