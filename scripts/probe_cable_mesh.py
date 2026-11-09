"""Read-only upstream cable tessellation diagnosis; never repairs a mesh."""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np
from bsa.cad_ifc import mesh_properties
from bsa.circular_geometry import configure
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase import ROOT


def topology(vertices, faces):
    directed = Counter((int(a), int(b)) for tri in faces for a, b in zip(tri, np.roll(tri, -1)))
    edges = Counter()
    for (a, b), count in directed.items():
        edges[tuple(sorted((a, b)))] += count
    return dict(vertices=len(vertices), triangles=len(faces), edges=len(edges),
                euler=len(vertices)-len(edges)+len(faces),
                non_two_face_edges=sum(n != 2 for n in edges.values()),
                inconsistent_direction_edges=sum(directed[a, b] != directed[b, a] for a, b in edges),
                duplicate_triangles=len(faces)-len({tuple(sorted(map(int, tri))) for tri in faces}),
                bounds_m=[vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()])


def run(ifc, out):
    ifc, out = Path(ifc).resolve(), Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists() or out == ifc:
        raise ProjectError('new repository report path required')
    before = digest(ifc)
    model = ifcopenshell.open(str(ifc))
    cables = model.by_type('IfcCableSegment')
    if not cables:
        raise ProjectError('no cable segments to diagnose')
    results = []
    for options in ({}, {'reorient-shells': True}, {'unify-shapes': True}, {'no-clean-triangulation': True}):
        settings = ifcopenshell.geom.settings()
        settings.set('use-world-coords', True)
        configure(settings)
        for key, value in options.items():
            settings.set(key, value)
        for cable in cables:
            row = dict(guid=cable.GlobalId, settings=options, accepted=False)
            try:
                shape = ifcopenshell.geom.create_shape(settings, cable)
                vertices = np.array(shape.geometry.verts).reshape(-1, 3)
                faces = np.array(shape.geometry.faces).reshape(-1, 3)
                row.update(topology(vertices, faces))
                props = mesh_properties(vertices, faces)
                row.update(accepted=True, volume_m3=props['volume'])
            except (ProjectError, RuntimeError, ValueError) as exc:
                row['error'] = str(exc)
            results.append(row)
    if digest(ifc) != before:
        raise ProjectError('IFC changed during diagnosis')
    report = dict(ifc_sha256=before, input_unchanged=True,
                  versions={k: importlib.metadata.version(k) for k in ('ifcopenshell', 'manifold3d', 'numpy')},
                  results=results, design_accepted=False,
                  scope='Read-only diagnostic, not a geometry repair or electrical design acceptance')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ifc', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.ifc, args.out)
    print(json.dumps(dict(cases=len(result['results']), accepted=sum(r['accepted'] for r in result['results']))))
