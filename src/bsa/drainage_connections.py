"""Source-pinned APP-164 declared fixture connection review, not model verification."""
import argparse
import json
from pathlib import Path

from .cli import digest
from .drainage_scope import separate_discharge_floors
from .plumbing_demand_study import pinned_references

OFFICIAL_SHA256 = 'af42aafd00e67afc2abaf5601d433737a266e4797b5cc897c96d511539219b4b'


def review(scope, fixtures, *, inventory_complete, inventory_source):
    """Review one declared stack and all fitments on its restricted floors.

    Rows represent individual fitments, not assumed aggregate DU groups.
    Independent lowest-floor pipes may combine subject to other requirements;
    no requirement for one pipe per fitment is inferred here.
    """
    selection = separate_discharge_floors(**scope)
    if type(inventory_complete) not in (bool, type(None)):
        raise ValueError('Inventory completeness must be Boolean or unknown')
    if not isinstance(inventory_source, str) or not inventory_source.strip():
        raise ValueError('Explicit inventory source required, including for an empty inventory')
    if not isinstance(fixtures, list):
        raise ValueError('Fixture inventory list required')
    seen = set()
    for row in fixtures:
        if not isinstance(row, dict) or set(row) != {'id', 'floor_offset', 'connected_to_stack', 'separate_to_manhole', 'source'}:
            raise ValueError('Exact fixture identity, floor, connections and source required')
        if not isinstance(row['id'], str) or not row['id'].strip() or row['id'] in seen:
            raise ValueError('Unique fixture identity required')
        seen.add(row['id'])
        if row['floor_offset'] is not None and type(row['floor_offset']) is not int:
            raise ValueError('Floor offset must be an integer or unknown')
        if any(type(row[k]) not in (bool, type(None)) for k in ('connected_to_stack', 'separate_to_manhole')):
            raise ValueError('Connection facts must be Boolean or unknown')
        if not isinstance(row['source'], str) or not row['source'].strip():
            raise ValueError('Fixture connection evidence reference required')
    checks = []
    offsets = selection['separate_discharge_floor_offsets']
    if offsets is not None:
        for row in fixtures:
            floor = row['floor_offset']
            if floor is None:
                status = 'pending'
            elif floor not in offsets:
                status = 'outside_selected_floors'
            elif row['connected_to_stack'] is True or row['separate_to_manhole'] is False:
                status = 'fail'
            elif row['connected_to_stack'] is None or row['separate_to_manhole'] is None:
                status = 'pending'
            else:
                status = 'pass'
            checks.append(dict(row, status=status))
    failed = any(r['status'] == 'fail' for r in checks)
    pending = (selection['status'] != 'selected' or inventory_complete is not True
               or any(r['status'] == 'pending' for r in checks))
    status = 'fail' if failed else 'pending' if pending else 'pass'
    return dict(status=status, selection=selection, fixtures=checks,
                inventory_complete=inventory_complete, inventory_source=inventory_source,
                supported_checks_pass=status == 'pass', design_accepted=False,
                regulatory_compliance='not_established',
                scope='Declared single-stack connection facts only; no saved-model verification, capacity, venting, offset clearance or full conformity')


def run(project, output):
    project, output = (Path(p).resolve() for p in (project, output))
    before = digest(project)
    spec = json.loads(project.read_text(encoding='utf-8'))
    if set(spec) != {'scope', 'fixtures', 'inventory_complete', 'inventory_source', 'references', 'official_reference'}:
        raise ValueError('Exact drainage connection study fields required')
    pins = pinned_references(project, spec)
    if pins[str(project)] != before:
        raise ValueError('Project changed during validation')
    official = spec['official_reference']
    if not isinstance(official, str) or spec['references'].get(official) != OFFICIAL_SHA256:
        raise ValueError('Pinned November 2023 APP-164 official reference required')
    if output.exists() or any(output == Path(p) or output in Path(p).parents for p in pins):
        raise ValueError('New output outside sources required')
    from . import drainage_scope
    pins.update({str(p): digest(p) for p in (Path(__file__).resolve(), Path(drainage_scope.__file__).resolve())})
    result = review(spec['scope'], spec['fixtures'], inventory_complete=spec['inventory_complete'],
                    inventory_source=spec['inventory_source'])
    if any(digest(Path(p)) != sha for p, sha in pins.items()):
        raise ValueError('Study source changed during execution')
    result.update(inputs=pins, official_reference=official)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = run(args.project, args.out)
    print(result['status'], 'complete engineering acceptance pending')
    raise SystemExit(2)
