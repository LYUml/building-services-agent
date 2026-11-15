"""Check linear SU2 boundary incidence; explicitly remove internal wall markers.

This adapter checks saved connectivity, not element Jacobians, source geometry,
mesh independence, flow convergence or engineering acceptance.
"""
from collections import Counter
import hashlib
import math


PATTERNS = {10: ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)),
            13: ((0, 1, 2), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5))}


def check(data: bytes, *, remove_internal_walls=False):
    if type(remove_internal_walls) is not bool:
        raise ValueError('Explicit boolean repair flag required')
    lines = data.splitlines(keepends=True)

    def header(index, name, allow_zero=False):
        if index >= len(lines):
            raise ValueError('Incomplete mesh')
        parts = lines[index].split(b'=')
        if len(parts) != 2 or parts[0].strip() != name.encode():
            raise ValueError('Expected '+name)
        number = int(parts[1])
        if number < 0 or (number == 0 and not allow_zero):
            raise ValueError('Positive mesh counts required')
        return number

    if header(0, 'NDIME') != 3:
        raise ValueError('Only single-zone three-dimensional meshes supported')
    ne = header(1, 'NELEM')
    if 2+ne >= len(lines):
        raise ValueError('Incomplete element table')

    def cell(line):
        row = list(map(int, line.split()))
        if not row or row[0] not in PATTERNS:
            raise ValueError('Only linear tetrahedra and prisms supported')
        count = 4 if row[0] == 10 else 6
        if len(row) not in (count+1, count+2):
            raise ValueError('Invalid volume connectivity')
        nodes = row[1:count+1]
        if len(set(nodes)) != count:
            raise ValueError('Repeated volume vertex')
        return row[0], nodes

    faces, referenced, cells_seen = Counter(), set(), set()
    for line in lines[2:2+ne]:
        kind, nodes = cell(line)
        identity = (kind, tuple(sorted(nodes)))
        if identity in cells_seen:
            raise ValueError('Duplicate volume cell')
        cells_seen.add(identity)
        referenced.update(nodes)
        faces.update(tuple(sorted(nodes[i] for i in indices)) for indices in PATTERNS[kind])
    if max(faces.values()) > 2:
        raise ValueError('Nonmanifold volume-face incidence')
    del cells_seen
    index = 2+ne
    nn = header(index, 'NPOIN')
    index += 1
    if index+nn >= len(lines) or referenced != set(range(nn)):
        raise ValueError('Complete zero-based volume point references required')
    points = []
    for i, line in enumerate(lines[index:index+nn]):
        row = line.split()
        if len(row) != 4 or int(row[3]) != i:
            raise ValueError('Sequential explicit point identifiers required')
        xyz = tuple(map(float, row[:3]))
        if not all(math.isfinite(v) for v in xyz):
            raise ValueError('Finite coordinates required')
        points.append(xyz)
    index += nn
    nm = header(index, 'NMARK')
    prefix = b''.join(lines[:index+1])
    index += 1
    original, kept, groups, names = set(), {}, [], set()
    removed = Counter()
    for _ in range(nm):
        if index+1 >= len(lines):
            raise ValueError('Incomplete boundary table')
        tag_line = lines[index]
        parts = tag_line.split(b'=')
        if len(parts) != 2 or parts[0].strip() != b'MARKER_TAG':
            raise ValueError('Expected marker tag')
        name = parts[1].strip().decode('utf-8')
        if not name or name in names:
            raise ValueError('Unique nonempty marker names required')
        names.add(name)
        count = header(index+1, 'MARKER_ELEMS', allow_zero=True)
        index += 2
        if index+count > len(lines):
            raise ValueError('Incomplete boundary faces')
        entries = []
        for line in lines[index:index+count]:
            row = list(map(int, line.split()))
            if not row or row[0] not in (5, 9):
                raise ValueError('Only linear boundary triangles/quadrilaterals supported')
            size = 3 if row[0] == 5 else 4
            if len(row) != size+1 or len(set(row[1:])) != size:
                raise ValueError('Invalid boundary connectivity')
            nodes = row[1:]
            key = tuple(sorted(nodes))
            if key in original:
                raise ValueError('Duplicate boundary face or conflicting marker ownership')
            original.add(key)
            incidence = faces.get(key, 0)
            if incidence == 0:
                raise ValueError('Boundary face is absent from volume connectivity')
            if incidence == 2:
                if name != 'wall' or not remove_internal_walls:
                    raise ValueError('Internal boundary face: only explicit wall-marker repair permitted')
                removed[name] += 1
            else:
                kept[key] = (name, nodes)
                entries.append(line)
        groups.append((tag_line, entries))
        index += count
    if any(line.strip() for line in lines[index:]):
        raise ValueError('Unsupported trailing mesh sections')
    exterior = {key for key, count in faces.items() if count == 1}
    if not exterior:
        raise ValueError('Nonempty exterior required')
    if set(kept) != exterior:
        raise ValueError('Missing exterior boundary faces; labels cannot be inferred')

    owners = {}
    for line in lines[2:2+ne]:
        kind, nodes = cell(line)
        center = None
        for indices in PATTERNS[kind]:
            key = tuple(sorted(nodes[i] for i in indices))
            if key in kept:
                if center is None:
                    center = tuple(sum(points[n][j] for n in nodes)/len(nodes) for j in range(3))
                owners[key] = center
    for key, (name, nodes) in kept.items():
        triangles = [nodes] if len(nodes) == 3 else [nodes[:3], [nodes[0], nodes[2], nodes[3]]]
        for triangle in triangles:
            a, b, c = (points[n] for n in triangle)
            u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            center = tuple(sum(points[n][j] for n in triangle)/3 for j in range(3))
            dot = sum(normal[j]*(center[j]-owners[key][j]) for j in range(3))
            if not math.isfinite(dot) or dot <= 0:
                raise ValueError('Inward or degenerate boundary orientation: '+name)

    output = data
    if removed:
        newline = b'\r\n' if lines[0].endswith(b'\r\n') else b'\n'
        chunks = [prefix]
        for tag_line, entries in groups:
            chunks += [tag_line, f'MARKER_ELEMS= {len(entries)}'.encode()+newline, *entries]
        chunks += lines[index:]
        output = b''.join(chunks)
        if not output.startswith(prefix):
            raise ValueError('Volume connectivity or point coordinates changed')
    report = dict(points=nn, volume_cells=ne, exterior_faces=len(exterior),
                  removed_internal_wall_faces=dict(removed), boundary_face_incidence_pass=True,
                  outward_boundary_orientation_pass=True,
                  source_sha256=hashlib.sha256(data).hexdigest(),
                  output_sha256=hashlib.sha256(output).hexdigest(),
                  volume_and_point_prefix_sha256=hashlib.sha256(prefix).hexdigest(),
                  volume_and_coordinates_byte_unchanged=True, engineering_accepted=False,
                  scope='Boundary connectivity and orientation only. Separate source geometry, Jacobian, port, mesh, convergence and physical checks required.')
    return output, report


def main():
    import argparse
    import json
    from pathlib import Path
    from .workspace import project_root
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--output-mesh')
    parser.add_argument('--remove-internal-walls', action='store_true')
    args = parser.parse_args()
    if args.remove_internal_walls and not args.output_mesh:
        parser.error('Explicit repair requires a new output mesh')
    root = project_root()
    if root is None:
        raise ValueError('Explicit host BSA_PROJECT_ROOT required')

    def path(value):
        p = (root/value).resolve()
        if not p.is_relative_to(root):
            raise ValueError('All paths must remain in host project')
        return p

    source, report_file = path(args.mesh), path(args.report)
    output_file = path(args.output_mesh) if args.output_mesh else None
    destinations = [p for p in (report_file, output_file) if p is not None]
    if len(set(destinations)) != len(destinations) or source in destinations or any(p.exists() for p in destinations):
        raise ValueError('Preserve sources and existing outputs; choose distinct new paths')
    before = source.stat()
    data = source.read_bytes()
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(data) != after.st_size:
        raise ValueError('Mesh changed during read; retry the same run')
    output, report = check(data, remove_internal_walls=args.remove_internal_walls)
    report['method_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if output_file is not None:
        with output_file.open('xb') as stream:
            stream.write(output)
    with report_file.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(removed_internal_wall_faces=report['removed_internal_wall_faces'], engineering_accepted=False)))


if __name__ == '__main__':
    main()
