"""Diagnose saved Revit pipe/fitting inventory; never certify a complete system."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from .engine import ProjectError
from .revit_revision import audit_pipe


def diagnose(inventory, tolerance_m):
    if type(tolerance_m) not in (int, float) or not math.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ProjectError('A finite positive diagnostic tolerance in metres is required')
    if inventory.get('units') != 'metres':
        raise ProjectError('Inventory must explicitly use metres')
    nodes, owners, issues, pending, open_ports = {}, set(), [], [], []

    def point(value):
        if not isinstance(value, list) or len(value) != 3 or any(
            type(x) not in (int, float) or not math.isfinite(x) for x in value
        ):
            raise ProjectError('Invalid physical connector coordinates')
        return value

    def key(owner, connector):
        if not isinstance(owner, str) or not owner.strip() or type(connector) is not int:
            raise ProjectError('Invalid connector identity')
        return owner, connector

    for kind in ('pipes', 'fittings'):
        if not isinstance(inventory.get(kind), list):
            raise ProjectError('Pipe and fitting inventory arrays are required')
        for item in inventory[kind]:
            owner = item.get('unique_id')
            if not isinstance(owner, str) or not owner or owner in owners:
                raise ProjectError('Missing or duplicate element identity')
            owners.add(owner)
            connectors = item.get('connectors')
            if connectors is None and kind == 'fittings' and item.get('connector_manager_available') is False:
                pending.append(dict(owner=owner, reason='missing_connector_manager'))
                continue
            if not isinstance(connectors, list) or not connectors:
                raise ProjectError('Missing or empty connector collection')
            for c in connectors:
                ident = key(owner, c.get('id'))
                if ident in nodes:
                    raise ProjectError('Duplicate connector identity')
                if not isinstance(c.get('references'), list):
                    raise ProjectError('Missing connector references')
                if not isinstance(c.get('domain'), str) or not isinstance(c.get('connector_type'), str):
                    raise ProjectError('Missing connector domain/type')
                if c['connector_type'] != 'Logical':
                    point(c.get('origin_m'))
                    if type(c.get('physically_connected')) is not bool:
                        raise ProjectError('Missing physical connection observation')
                nodes[ident] = c

    if not nodes:
        raise ProjectError('Empty inventory cannot establish connectivity')
    directed_checks = set()
    for ident, c in nodes.items():
        if c['connector_type'] == 'Logical':
            continue
        physical_refs = []
        targets = set()
        for ref in c['references']:
            target = key(ref.get('owner_unique_id'), ref.get('connector_id'))
            if target in targets or target[0] == ident[0]:
                raise ProjectError('Duplicate or self-owner external reference')
            targets.add(target)
            if ref.get('connector_type') == 'Logical':
                continue
            physical_refs.append(target)
            if target not in nodes:
                pending.append(dict(port=ident, target=target, reason='target_outside_inventory'))
                continue
            other = nodes[target]
            reasons = []
            if other['connector_type'] == 'Logical' or ref.get('connector_type') != other['connector_type']:
                reasons.append('reference_type_mismatch')
            if other['domain'] != c['domain'] or ref.get('domain') != other['domain']:
                reasons.append('domain_mismatch')
            reverse = [r for r in other['references'] if
                       (r.get('owner_unique_id'), r.get('connector_id')) == ident]
            if not reverse or ref.get('reciprocal_reference') is not True:
                reasons.append('missing_reciprocal_reference')
            if ref.get('api_connected_to') is not True or not reverse or reverse[0].get('api_connected_to') is not True:
                reasons.append('api_relation_not_confirmed')
            if c['physically_connected'] is not True or other.get('physically_connected') is not True:
                reasons.append('physical_connection_not_confirmed')
            if other['connector_type'] != 'Logical':
                distance = math.dist(c['origin_m'], other['origin_m'])
                if distance > tolerance_m:
                    reasons.append('endpoint_separation')
                if math.dist(point(ref.get('origin_m')), other['origin_m']) > tolerance_m:
                    reasons.append('reference_position_mismatch')
                recorded = ref.get('separation_m')
                if type(recorded) not in (int, float) or not math.isfinite(recorded) or recorded < 0:
                    raise ProjectError('Missing or invalid recorded separation')
                if abs(recorded - distance) > tolerance_m:
                    reasons.append('recorded_separation_mismatch')
            if reasons:
                issues.append(dict(port=ident, target=target, reasons=reasons))
            else:
                directed_checks.add((ident, target))
        if not physical_refs:
            if c['physically_connected']:
                issues.append(dict(port=ident, reasons=['physical_flag_without_physical_reference']))
            else:
                open_ports.append(ident)
    # A passing direction cannot mask contradictory metadata in the reverse record.
    edges = {tuple(sorted((a, b))) for a, b in directed_checks if (b, a) in directed_checks}
    revision_checks = [dict(owner=p['unique_id'], **audit_pipe(p, tolerance_m)) for p in inventory['pipes']]
    for row in revision_checks:
        if row['status'] == 'fail':
            issues.append(dict(owner=row['owner'], reasons=row['reasons']))
        elif row['status'] == 'pending':
            pending.append(dict(owner=row['owner'], reason='no_creation_provenance'))
    return dict(scope='Saved pipe/fitting connector evidence and creation-request comparison only',
                diagnostic_status='fail' if issues else 'pending', issues=issues, pending=pending,
                revision_checks=revision_checks,
                observed_open_ports=open_ports, consistent_reference_pairs=sorted(edges),
                tolerance_m=tolerance_m, design_accepted=False, connected_system_verified=False,
                unresolved=['Host execution and saved reopening', 'Declared terminals and complete equipment/accessory coverage',
                            'Internal fitting connectivity, system traversal and engineering acceptance'])


def run(inventory, model, out, tolerance_m):
    root = Path(__file__).resolve().parents[2]
    paths = [Path(p).resolve() for p in (inventory, model, out)]
    if any(not p.is_relative_to(root) for p in paths) or paths[2].exists():
        raise ProjectError('Use repository-local artifacts and a new output path')
    raw, model = paths[0].read_bytes(), paths[1].read_bytes()
    data = json.loads(raw)
    digest = lambda b: hashlib.sha256(b).hexdigest()
    if not isinstance(data.get('document_path'), str) or Path(data['document_path']).resolve() != paths[1] or digest(model) != data.get('saved_rvt_sha256'):
        raise ProjectError('Inventory does not match the selected saved model')
    result = diagnose(data, tolerance_m)
    result.update(inventory_sha256=digest(raw), saved_rvt_sha256=digest(model))
    if paths[0].read_bytes() != raw or paths[1].read_bytes() != model:
        raise ProjectError('Input changed during diagnosis')
    paths[2].parent.mkdir(parents=True, exist_ok=True)
    with paths[2].open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--tolerance-m', type=float, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inventory, args.model, args.out, args.tolerance_m)
    print(json.dumps(result))
    return 2  # A consistent inventory is not complete system acceptance.


if __name__ == '__main__':
    raise SystemExit(main())
