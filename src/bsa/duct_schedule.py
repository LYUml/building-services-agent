"""Batch equivalent-round section checks; no topology or fan-duty acceptance."""
import csv
import hashlib
import json
import math
from pathlib import Path
from .duct_equivalent import calculate, select_sizes


def run(project_path, output, *, allocation_path=None, allocation_sha256=None):
    project_path, output = Path(project_path).resolve(), Path(output).resolve()
    raw = project_path.read_bytes()
    project = json.loads(raw.decode('utf-8-sig'))
    if output.exists() or output == project_path or output in project_path.parents:
        raise ValueError('New output directory separate from source required')
    basis = project.get('basis')
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError('Explicit source/assumption basis required')
    inherited=None;aggregation=None
    if allocation_path is not None:
        from .air_tree_flow import aggregate
        allocation_path=Path(allocation_path).resolve();inherited=allocation_path.read_bytes()
        if hashlib.sha256(inherited).hexdigest()!=allocation_sha256:
            raise ValueError('Allocation producer hash mismatch')
        if output==allocation_path or output in allocation_path.parents:
            raise ValueError('Output must not contain producer')
        if any('flow_m3_s' in s for s in project['sections']):
            raise ValueError('Inherited section flows cannot be overridden')
        allocation=json.loads(inherited.decode('utf-8-sig'))
        aggregation=aggregate(project['tree'],allocation['terminals'])
        flows=aggregation['section_flow_L_s']
        if set(flows)!={s['id'] for s in project['sections']}:
            raise ValueError('Tree and schedule section identities must match exactly')
        for section in project['sections']:section['flow_m3_s']=flows[section['id']]/1000
    elif allocation_sha256 is not None or 'tree' in project:
        raise ValueError('Tree schedule requires inherited allocation')
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
        selection=None
        if 'candidates' in section:
            if 'width_m' in section or 'height_m' in section:
                raise ValueError('Choose supplied dimensions or candidate sizing, not both')
            if not isinstance(section.get('candidate_basis'),str) or not section['candidate_basis'].strip():
                raise ValueError('Explicit candidate size source/assumption required')
            selection=select_sizes(candidates=section['candidates'],
                max_velocity_m_s=limits['actual_velocity_m_s'],
                max_friction_Pa_m=limits['friction_Pa_m'],
                max_aspect_ratio=limits['aspect_ratio'],
                flow_m3_s=section['flow_m3_s'],**project['air'])
            chosen=selection['selected']
            inputs=dict(flow_m3_s=section['flow_m3_s'])
            if chosen:
                inputs.update(width_m=chosen['width_m'],height_m=chosen['height_m'])
                calculation=chosen['calculation'];failures=[]
            else:
                calculation=None;failures=['no_feasible_size']
        else:
            inputs = {k: section[k] for k in ('flow_m3_s', 'width_m', 'height_m')}
            calculation = calculate(**inputs, **project['air'])
            failures = [key for key, limit in limits.items() if calculation[key] > limit]
        row=dict(id=name,inputs=inputs,calculation=calculation,limits=limits,failures=failures)
        if selection is not None:
            row.update(selection=selection,candidate_basis=section['candidate_basis'])
        rows.append(row)
    if not rows:
        raise ValueError('Nonempty section list required')
    if project_path.read_bytes() != raw:
        raise ValueError('Source changed during calculation')
    result = dict(input_sha256=hashlib.sha256(raw).hexdigest(), basis=basis,
                  air=project['air'], sections=rows,
                  status='fail' if any(r['failures'] for r in rows) else 'pass',
                  scope='Supplied section dimensions and prescribed flows only; source applicability, topology, local losses, fan selection and geometry require separate checks',
                  design_accepted=False)
    if inherited is not None:
        if allocation_path.read_bytes()!=inherited:raise ValueError('Allocation producer changed during schedule')
        result['allocation_input']={str(allocation_path):allocation_sha256}
        result['flow_aggregation']=aggregation
        result['scope']='Inherited prescribed terminal demands aggregated through declared tree; section checks only, physical connections, local losses, fan duty and geometry remain pending'
    if any('selection' in r for r in rows):
        result['scope']+='; candidate sizing ranks feasible sections by area/perimeter, not network pressure or spatial fit'
    output.mkdir(parents=True)
    (output/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (output/'schedule.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Section', 'Flow L/s', 'Width mm', 'Height mm', 'Velocity m/s', 'Friction Pa/m', 'Aspect ratio', 'Failed criteria'])
        for r in rows:
            i, c = r['inputs'], r['calculation']
            if c is None:
                writer.writerow([r['id'],i['flow_m3_s']*1000,'','','','','',';'.join(r['failures'])])
                continue
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
