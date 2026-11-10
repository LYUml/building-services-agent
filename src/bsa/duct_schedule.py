"""Batch equivalent-round section checks; no topology or fan-duty acceptance."""
import csv
import hashlib
import json
import math
from pathlib import Path
from .duct_equivalent import calculate


def run(project_path, output):
    project_path, output = Path(project_path).resolve(), Path(output).resolve()
    raw = project_path.read_bytes()
    project = json.loads(raw.decode('utf-8-sig'))
    if output.exists() or output == project_path or output in project_path.parents:
        raise ValueError('New output directory separate from source required')
    basis = project.get('basis')
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError('Explicit source/assumption basis required')
    rows, ids = [], set()
    for section in project['sections']:
        name = section['id']
        if not isinstance(name, str) or not name.strip() or name in ids:
            raise ValueError('Unique nonempty section IDs required')
        ids.add(name)
        limits = section['limits']
        if set(limits) != {'actual_velocity_m_s', 'friction_Pa_m', 'aspect_ratio'}:
            raise ValueError('Explicit velocity, friction and aspect limits required')
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in limits.values()) or limits['aspect_ratio'] < 1:
            raise ValueError('Invalid section limits')
        inputs = {k: section[k] for k in ('flow_m3_s', 'width_m', 'height_m')}
        calculation = calculate(**inputs, **project['air'])
        failures = [key for key, limit in limits.items() if calculation[key] > limit]
        rows.append(dict(id=name, inputs=inputs, calculation=calculation,
                         limits=limits, failures=failures))
    if not rows:
        raise ValueError('Nonempty section list required')
    if project_path.read_bytes() != raw:
        raise ValueError('Source changed during calculation')
    result = dict(input_sha256=hashlib.sha256(raw).hexdigest(), basis=basis,
                  air=project['air'], sections=rows,
                  status='fail' if any(r['failures'] for r in rows) else 'pass',
                  scope='Supplied section dimensions and prescribed flows only; source applicability, topology, local losses, fan selection and geometry require separate checks',
                  design_accepted=False)
    output.mkdir(parents=True)
    (output/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (output/'schedule.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Section', 'Flow L/s', 'Width mm', 'Height mm', 'Velocity m/s', 'Friction Pa/m', 'Aspect ratio', 'Failed criteria'])
        for r in rows:
            i, c = r['inputs'], r['calculation']
            writer.writerow([r['id'], i['flow_m3_s']*1000, i['width_m']*1000,
                             i['height_m']*1000, c['actual_velocity_m_s'],
                             c['friction_Pa_m'], c['aspect_ratio'], ';'.join(r['failures'])])
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = run(args.project, args.out)
    print(result['status'], len(result['sections']), 'sections; design acceptance pending')
    raise SystemExit(0 if result['status'] == 'pass' else 2)
