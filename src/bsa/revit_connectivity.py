"""Diagnose saved Revit pipe/fitting inventory; never certify a complete system."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from .engine import ProjectError
from .revit_revision import audit_pipe
from . import workspace


def compare_expected(intent, physical_ports, observed, confirmed):
    if (not isinstance(intent, dict) or set(intent) != {'source', 'required_pairs'}
            or not isinstance(intent['source'], str) or not intent['source'].strip()
            or not isinstance(intent['required_pairs'], list) or not intent['required_pairs']):
        raise ProjectError('Expected connections require a source locator and nonempty required_pairs')
    required, scoped_ports = set(), set()
    for pair in intent['required_pairs']:
        if not isinstance(pair, list) or len(pair) != 2 or any(
            not isinstance(port, list) or len(port) != 2
            or not isinstance(port[0], str) or not port[0].strip() or type(port[1]) is not int
            for port in pair
        ):
            raise ProjectError('Expected pair must contain two [owner unique ID, connector ID] endpoints')
        a, b = map(tuple, pair)
        if a[0] == b[0] or a in scoped_ports or b in scoped_ports:
            raise ProjectError('Expected connections require distinct owners and one declared peer per port')
        scoped_ports.update((a, b))
        required.add(tuple(sorted((a, b))))
    missing, unconfirmed, unavailable = [], [], []
    for pair in sorted(required - confirmed):
        if set(pair) - physical_ports:
            unavailable.append(pair)
        elif pair in observed:
            unconfirmed.append(pair)
        else:
            missing.append(pair)
    unexpected = sorted(pair for pair in observed - required if scoped_ports.intersection(pair))
    return dict(source=intent['source'], expected_pair_count=len(required),
                matched_pairs=sorted(required & confirmed), missing_pairs=missing,
                unconfirmed_pairs=unconfirmed, unavailable_pairs=unavailable, unexpected_pairs=unexpected,
                status='fail' if missing or unconfirmed or unexpected else 'pending' if unavailable else 'pass')


def diagnose(inventory, tolerance_m, *, expected_connections=None):
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
    directed_checks, observed = set(), set()
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
            observed.add(tuple(sorted((ident, target))))
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
    result = dict(scope='Saved pipe/fitting connector evidence and creation-request comparison only',
                diagnostic_status='fail' if issues else 'pending', issues=issues, pending=pending,
                revision_checks=revision_checks,
                observed_open_ports=open_ports, consistent_reference_pairs=sorted(edges),
                tolerance_m=tolerance_m, design_accepted=False, connected_system_verified=False,
                unresolved=['Host execution and saved reopening', 'Declared terminals and complete equipment/accessory coverage',
                            'Internal fitting connectivity, system traversal and engineering acceptance'])
    if expected_connections is not None:
        physical_ports = {ident for ident, c in nodes.items() if c['connector_type'] != 'Logical'}
        comparison = compare_expected(expected_connections, physical_ports, observed, edges)
        result['expected_connections'] = comparison
        if comparison['status'] == 'fail':
            result['diagnostic_status'] = 'fail'
    return result


def run(inventory, model, out, tolerance_m, *, expected_connections=None):
    inventory_path, model_path, output_path = (Path(p).resolve() for p in (inventory, model, out))
    basis = Path(expected_connections).resolve() if expected_connections is not None else None
    paths = (inventory_path, model_path, output_path, basis)
    if not all(workspace.allowed(p) for p in paths if p is not None) or output_path.exists():
        raise ProjectError('Use permitted workspace artifacts and a new output path')
    raw, model = inventory_path.read_bytes(), model_path.read_bytes()
    data = json.loads(raw)
    digest = lambda b: hashlib.sha256(b).hexdigest()
    if not isinstance(data.get('document_path'), str) or Path(data['document_path']).resolve() != model_path or digest(model) != data.get('saved_rvt_sha256'):
        raise ProjectError('Inventory does not match the selected saved model')
    basis_raw = basis.read_bytes() if basis is not None else None
    intent = json.loads(basis_raw) if basis_raw is not None else None
    if basis is not None and intent is None:
        raise ProjectError('Expected connection evidence must be an object')
    result = diagnose(data, tolerance_m, expected_connections=intent)
    result.update(inventory_sha256=digest(raw), saved_rvt_sha256=digest(model))
    if basis_raw is not None:
        result['expected_connections_sha256'] = digest(basis_raw)
    if (inventory_path.read_bytes() != raw or model_path.read_bytes() != model
            or (basis is not None and basis.read_bytes() != basis_raw)):
        raise ProjectError('Input changed during diagnosis')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return result


def add_arguments(parser):
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--tolerance-m', type=float, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-connections', type=Path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    result = run(args.inventory, args.model, args.out, args.tolerance_m,
                 expected_connections=args.expected_connections)
    print(json.dumps(result))
    return 2  # A consistent inventory is not complete system acceptance.


if __name__ == '__main__':
    raise SystemExit(main())
