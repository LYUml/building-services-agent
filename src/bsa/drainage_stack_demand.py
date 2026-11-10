"""Bind declared APP-164 fixture identities to a scoped stack DU calculation."""
import argparse
import json
from pathlib import Path

from .cli import digest
from .drainage_connections import review, run as connection_run
from .plumbing_demand import discharge_units
from .plumbing_demand_study import pinned_references


def calculate(project, basis):
    if set(basis) != {'fixture_units', 'frequency_factor', 'full_stack_inventory_verified',
                     'frequency_classification_verified', 'basis', 'references'}:
        raise ValueError('Exact stack demand basis fields required')
    facts = [basis['full_stack_inventory_verified'], basis['frequency_classification_verified']]
    if any(type(v) not in (bool, type(None)) for v in facts):
        raise ValueError('Boolean or unknown full-stack inventory and frequency facts required')
    if not isinstance(basis['basis'], str) or not basis['basis'].strip():
        raise ValueError('Explicit stack inventory and method basis required')
    factor = basis['frequency_factor']
    if not isinstance(factor, dict) or set(factor) != {'value', 'source', 'classification'}:
        raise ValueError('Classified frequency factor required')
    units = basis['fixture_units']
    if not isinstance(units, dict) or set(units) != {r['id'] for r in project['fixtures']}:
        raise ValueError('DU identities must exactly cover the original individual fixture inventory')
    rows = []
    included, excluded, unresolved = [], [], []
    for fixture in project['fixtures']:
        name = fixture['id']
        item = units[name]
        if not isinstance(item, dict) or set(item) != {'value', 'source', 'classification'}:
            raise ValueError('Each fixture DU requires value/source/classification')
        row = dict(id=name, count=1, DU_per_fixture=item['value'],
                   source=item['source'], classification=item['classification'])
        # Reuse the existing numeric/source validators, including excluded fixtures.
        discharge_units([row], frequency_factor=1, basis=basis['basis'])
        main, direct = fixture['connected_to_stack'], fixture['separate_to_manhole']
        if main is True and direct is False:
            included.append(name); rows.append(row)
        elif main is False and direct is True:
            excluded.append(name)
        else:
            unresolved.append(name)
    # Validate supplied factor even when the connection check prevents calculation.
    discharge_units([dict(id='factor_validation', count=1, DU_per_fixture=1,
                         source=factor['source'], classification=factor['classification'])],
                    frequency_factor=1 if factor['value'] is None else factor['value'], basis=basis['basis'])
    check = review(project['scope'], project['fixtures'],
                   inventory_complete=project['inventory_complete'], inventory_source=project['inventory_source'])
    status = ('fail' if check['status'] == 'fail' or any(v is False for v in facts)
              else 'pending' if check['status'] != 'pass' or any(v is None for v in facts) or unresolved or not rows or factor['value'] is None
              else 'calculated')
    calculation = discharge_units(rows, frequency_factor=factor['value'], basis=basis['basis']) if status == 'calculated' else None
    return dict(status=status, connection_review=check, included_fixture_ids=included,
                excluded_direct_manhole_fixture_ids=excluded, unresolved_fixture_ids=unresolved,
                frequency_factor=factor, full_stack_inventory_verified=facts[0],
                frequency_classification_verified=facts[1], basis=basis['basis'],
                calculation=calculation, design_accepted=False, regulatory_compliance='not_established',
                scope='Same declared individual inventory only; separate pipes excluded from this stack total, not from building demand; no saved geometry, other inflows or pipe/vent capacity verification')


def run(project, basis, output):
    project, basis, output = (Path(p).resolve() for p in (project, basis, output))
    project_sha, basis_sha = digest(project), digest(basis)
    spec = json.loads(project.read_text(encoding='utf-8'))
    settings = json.loads(basis.read_text(encoding='utf-8'))
    pins = pinned_references(project, spec)
    pins.update(pinned_references(basis, settings))
    if pins[str(project)] != project_sha or pins[str(basis)] != basis_sha:
        raise ValueError('Input changed during validation')
    from . import drainage_connections, drainage_scope, plumbing_demand, plumbing_demand_study
    pins.update({str(p): digest(p) for p in (Path(__file__).resolve(),
                Path(drainage_connections.__file__).resolve(), Path(drainage_scope.__file__).resolve(),
                Path(plumbing_demand.__file__).resolve(), Path(plumbing_demand_study.__file__).resolve())})
    if output.exists() or any(output == Path(p) or output in Path(p).parents for p in pins):
        raise ValueError('New output directory outside sources required')
    result = calculate(spec, settings)
    # Re-execute the original source-pinned connection adapter; do not trust a saved pass.
    connection_run(project, output / 'connections.json')
    if any(digest(Path(p)) != sha for p, sha in pins.items()):
        raise ValueError('Stack demand source changed during execution')
    result['inputs'] = pins
    (output / 'stack-demand.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project'); parser.add_argument('--basis', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = run(args.project, args.basis, args.out)
    print(result['status'], 'complete drainage acceptance pending')
    raise SystemExit(2)
