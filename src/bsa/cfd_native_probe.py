"""Extract saved SU2 native nodes on an explicitly declared line (no interpolation)."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path


def extract(mesh_data, field_data, start, end, fields, tolerance=1e-9):
    def vector(value):
        if len(value) != 3 or any(isinstance(x, bool) or not math.isfinite(x) for x in value):
            raise ValueError('Finite three-dimensional coordinates required')
        return tuple(float(x) for x in value)

    start, end = vector(start), vector(end)
    if isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Positive finite geometric tolerance required')
    delta = tuple(b-a for a, b in zip(start, end))
    length = math.sqrt(sum(x*x for x in delta))
    if length <= tolerance:
        raise ValueError('Distinct line endpoints required')
    direction = tuple(x/length for x in delta)
    if not fields or len(set(fields)) != len(fields) or any(not isinstance(x, str) for x in fields):
        raise ValueError('Unique explicit field names required')
    lines = mesh_data.decode('utf-8-sig').splitlines()
    if sum(line.strip().startswith('NDIME=') for line in lines) != 1:
        raise ValueError('Single-zone three-dimensional SU2 mesh required')
    if next(line.split('=')[1].strip() for line in lines if line.strip().startswith('NDIME=')) != '3':
        raise ValueError('Only three-dimensional native meshes supported')
    headers = [i for i, line in enumerate(lines) if line.strip().startswith('NPOIN=')]
    if len(headers) != 1:
        raise ValueError('Single point table required')
    index = headers[0]
    count = int(lines[index].split('=')[1])
    points = {}
    for line in lines[index+1:index+1+count]:
        values = line.split()
        if len(values) != 4:
            raise ValueError('Explicit SU2 point identifiers required')
        key = int(values[3])
        if key in points:
            raise ValueError('Duplicate mesh point')
        points[key] = vector(tuple(map(float, values[:3])))
    if set(points) != set(range(count)):
        raise ValueError('Complete zero-based mesh point identifiers required')
    reader = csv.DictReader(io.StringIO(field_data.decode('utf-8-sig')), skipinitialspace=True)
    names = reader.fieldnames
    if not names or len(names) != len(set(names)):
        raise ValueError('Unique saved-field headers required')
    required = {'PointID', 'x', 'y', 'z', *fields}
    if not required.issubset(names):
        raise ValueError('Required saved-field columns missing')
    seen, output = set(), []
    for row in reader:
        if None in row or any(x is None for x in row.values()):
            raise ValueError('Incomplete saved-field row')
        key = int(row['PointID'])
        if key not in points or key in seen:
            raise ValueError('Missing, foreign or duplicate saved-field point')
        seen.add(key)
        xyz = vector(tuple(float(row[k]) for k in ('x', 'y', 'z')))
        if math.dist(xyz, points[key]) > tolerance:
            raise ValueError('Saved-field coordinates do not match source mesh')
        values = {name: float(row[name]) for name in fields}
        if not all(math.isfinite(x) for x in values.values()):
            raise ValueError('Nonfinite requested field')
        along = sum((x-a)*d for x, a, d in zip(xyz, start, direction))
        projected = tuple(a+along*d for a, d in zip(start, direction))
        if -tolerance <= along <= length+tolerance and math.dist(xyz, projected) <= tolerance:
            output.append(dict(point_id=key, coordinates_m=list(xyz), distance_m=along, values=values))
    if seen != set(points) or len(output) < 2:
        raise ValueError('Complete saved field and at least two native line nodes required')
    output.sort(key=lambda row: (row['distance_m'], row['point_id']))
    return dict(nodes=output, mesh_points=count, engineering_accepted=False,
                scope='Native-node extraction only; no interpolation, connectivity, normalization, convergence or experimental acceptance.',
                provenance=dict(mesh_sha256=hashlib.sha256(mesh_data).hexdigest(),
                                field_sha256=hashlib.sha256(field_data).hexdigest()))


def main():
    import argparse
    from .workspace import project_root
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = project_root()
    if root is None:
        raise ValueError('Explicit host BSA_PROJECT_ROOT required')

    def path(value):
        result = (root/value).resolve()
        if not result.is_relative_to(root):
            raise ValueError('Paths must remain in host project')
        return result

    def stable(file):
        before = file.stat()
        data = file.read_bytes()
        after = file.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(data) != after.st_size:
            raise ValueError('Input changed during read; retry the same run')
        return data

    output = path(args.output)
    if output.exists():
        raise ValueError('Preserve existing evidence: select a new output')
    spec_data = stable(path(args.spec))
    spec = json.loads(spec_data)
    result = extract(stable(path(spec['mesh'])), stable(path(spec['field'])),
                     spec['start_m'], spec['end_m'], spec['fields'], spec.get('tolerance_m', 1e-9))
    result['provenance'].update(spec_sha256=hashlib.sha256(spec_data).hexdigest(),
                                method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(native_nodes=len(result['nodes']), engineering_accepted=False)))


if __name__ == '__main__':
    main()
