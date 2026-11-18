"""Reconcile a Revit creation receipt with a separately collected saved inventory."""
import argparse
import json
import math
from pathlib import Path, PureWindowsPath

from bsa import workspace
from bsa.revit_connectivity import reconstruct
from bsa.revit_request import validate_automation_request
from bsa.source_refs import file_hash


def verify(write_stage, creation, authored, inventory, reopen_preparation, tolerance_m):
    stage, creation, authored, inventory, reopen_preparation = (
        Path(path).resolve() for path in (write_stage, creation, authored, inventory, reopen_preparation))
    request = stage / 'pipe-request.json'
    preparation = stage / 'preparation.json'
    reopen_request = reopen_preparation.with_name('inventory-request.json')
    paths = (request, preparation, creation, authored, inventory, reopen_preparation, reopen_request)
    if not all(workspace.allowed(path) for path in paths):
        raise ValueError('Use files from the selected project workspace')
    pins = {path: file_hash(path) for path in paths}
    prepared, created, requested, reopened = (
        json.loads(path.read_bytes()) for path in (preparation, creation, request, inventory))
    if (prepared['operation'] != 'create-pipe'
            or pins[request] != prepared['request_sha256']
            or created['request_sha256'] != pins[request]
            or created['input_rvt_sha256'] != prepared['saved_rvt_sha256']
            or created['adapter_sha256'] != prepared['assembly_sha256']
            or created['saved_rvt_sha256'] != pins[authored]):
        raise ValueError('Creation evidence does not match the prepared request and saved RVT')
    if created.get('saved_reopen_verified') is not False or created.get('design_accepted') is not False:
        raise ValueError('Creation receipt must leave saved reopening and design acceptance unverified')
    transaction = created['transaction_result']
    if any(transaction.get(field) is not False for field in ('saved', 'connected_system_verified', 'design_accepted')):
        raise ValueError('Pipe transaction readback must leave saving, system verification and design acceptance unverified')
    validate_automation_request(requested, prepared['saved_rvt_sha256'])
    if pins[authored] == prepared['saved_rvt_sha256']:
        raise ValueError('Authored RVT must differ from the creation input')

    reopen_stage = json.loads(reopen_preparation.read_bytes())
    if (reopen_stage.get('operation') != 'inventory'
            or reopen_stage.get('request_sha256') != pins[reopen_request]
            or json.loads(reopen_request.read_bytes()) != {'SavedRvtSha256': pins[authored]}):
        raise ValueError('Reopen evidence does not match the staged inventory request and saved RVT')
    checked = reconstruct(inventory, authored, tolerance_m, automation_receipt=reopen_preparation)
    if (checked['inventory_sha256'] != pins[inventory]
            or checked['saved_rvt_sha256'] != pins[authored]
            or checked['automation_receipt_sha256'] != pins[reopen_preparation]):
        raise ValueError('Revit evidence changed during verification')
    identifier = transaction['unique_id']
    pipes = [pipe for pipe in reopened['pipes'] if pipe['unique_id'] == identifier]
    revisions = [row for row in checked['revision_checks'] if row['owner'] == identifier]
    if len(pipes) != 1 or len(revisions) != 1 or revisions[0]['status'] != 'consistent':
        raise ValueError('Reopened pipe identity or geometry does not match the transaction')
    for issue in checked['issues']:
        endpoints = (issue.get('port', (None,)), issue.get('target', (None,)))
        if any(port[0] == identifier for port in endpoints):
            raise ValueError(f"Reopened pipe has inconsistent connector evidence: {', '.join(issue['reasons'])}")
    for finding in checked['pending']:
        endpoints = (finding.get('port', (None,)), finding.get('target', (None,)))
        if finding.get('owner') == identifier or any(port[0] == identifier for port in endpoints):
            raise ValueError(f"Reopened pipe has unresolved connector evidence: {finding['reason']}")
    pipe = pipes[0]
    element_id = transaction.get('element_id')
    if (not isinstance(element_id, str) or not element_id.isascii() or not element_id.isdecimal()
            or int(element_id) <= 0 or pipe.get('id') != element_id):
        raise ValueError('Reopened pipe element_id differs from the creation readback')
    if sum(item.get('id') == element_id for group in ('pipes', 'fittings') for item in reopened[group]) != 1:
        raise ValueError(f'Reopened element_id {element_id} is shared by multiple pipe or fitting records')
    identity_fields = ('type_unique_id', 'system_type_unique_id', 'level_unique_id')
    attribute_matches = any(field in transaction for field in identity_fields)
    if attribute_matches:
        for field in identity_fields:
            if not isinstance(transaction.get(field), str) or transaction[field] != pipe[field]:
                raise ValueError(f'Reopened pipe {field} differs from the creation readback')
    for field in ('diameter_m', 'length_m'):
        recorded = transaction.get(field)
        if (type(recorded) not in (int, float) or not math.isfinite(recorded)
                or recorded <= 0 or abs(recorded - pipe[field]) > tolerance_m):
            raise ValueError(f'Reopened pipe {field} differs from the creation readback')
    if transaction.get('source') != requested['Source']:
        raise ValueError('Creation readback source differs from the staged request')
    connectors = pipe['connectors']
    connector_count = transaction.get('connector_count')
    if (type(connector_count) is not int or connector_count != 2 or len(connectors) != 2
            or any(c['domain'] != 'DomainPiping' or c['connector_type'] != 'End' for c in connectors)):
        raise ValueError('Reopened pipe must retain two piping end connectors')
    endpoints = pipe['endpoints_m']
    pairings = [
        [dict(connector_id=connector['id'], origin_m=connector['origin_m'],
              endpoint_m=endpoint, error_m=math.dist(connector['origin_m'], endpoint))
         for connector, endpoint in zip(order, endpoints, strict=True)]
        for order in (connectors, connectors[::-1])
    ]
    endpoint_matches = min(pairings, key=lambda rows: max(row['error_m'] for row in rows))
    worst = max(endpoint_matches, key=lambda row: row['error_m'])
    connector_error = worst['error_m']
    if connectors[0]['origin_m'] == connectors[1]['origin_m'] or connector_error > tolerance_m:
        raise ValueError('Reopened pipe connector origins do not match distinct curve endpoints '
                         f"(connector {worst['connector_id']}, deviation {connector_error:.6g} m)")
    if all(max(row['error_m'] for row in pairing) <= tolerance_m for pairing in pairings):
        raise ValueError('Reopened pipe connector-to-endpoint pairing is ambiguous at the declared tolerance')
    transaction_connectors = transaction.get('connectors')
    connector_readback = []
    if 'connectors' in transaction:
        if not isinstance(transaction_connectors, list) or len(transaction_connectors) != 2:
            raise ValueError('Creation readback requires two connector records')
        reopened_connectors = {connector['id']: connector for connector in connectors}
        seen = set()
        for connector in transaction_connectors:
            if not isinstance(connector, dict):
                raise ValueError('Invalid creation connector record')
            connector_id, origin = connector.get('id'), connector.get('origin_m')
            if (type(connector_id) is not int or connector_id not in reopened_connectors or connector_id in seen
                    or not isinstance(origin, list) or len(origin) != 3
                    or any(type(value) not in (int, float) or not math.isfinite(value) for value in origin)):
                raise ValueError(f'Reopened connector {connector_id} differs from the creation readback')
            reopened_connector = reopened_connectors[connector_id]
            reopened_origin = reopened_connector['origin_m']
            deviation = math.dist(origin, reopened_origin)
            if deviation > tolerance_m:
                raise ValueError(f'Reopened connector {connector_id} differs from the creation readback '
                                 f'(deviation {deviation:.6g} m)')
            creation_connected = connector.get('physically_connected')
            reopened_connected = reopened_connector.get('physically_connected')
            if 'physically_connected' in connector and (
                type(creation_connected) is not bool or creation_connected is not reopened_connected
            ):
                raise ValueError(f'Reopened connector {connector_id} physical connection flag differs from creation')
            creation_peers = connector.get('physical_references')
            reopened_peers = [
                dict(owner_unique_id=peer['owner_unique_id'], connector_id=peer['connector_id'])
                for peer in reopened_connector['references'] if peer['connector_type'] != 'Logical'
            ]
            if 'physical_references' in connector:
                if (not isinstance(creation_peers, list)
                        or any(not isinstance(peer, dict) or set(peer) != {'owner_unique_id', 'connector_id'}
                               or not isinstance(peer['owner_unique_id'], str) or type(peer['connector_id']) is not int
                               for peer in creation_peers)):
                    raise ValueError(f'Invalid creation peer references on connector {connector_id}')
                def peer_key(peer):
                    return peer['owner_unique_id'], peer['connector_id']
                if sorted(creation_peers, key=peer_key) != sorted(reopened_peers, key=peer_key):
                    before = sorted(map(peer_key, creation_peers))
                    after = sorted(map(peer_key, reopened_peers))
                    raise ValueError(f'Reopened connector {connector_id} physical peers differ from creation '
                                     f'(creation {before}, reopened {after})')
            connector_readback.append(dict(connector_id=connector_id, creation_origin_m=origin,
                                           reopened_origin_m=reopened_origin, deviation_m=deviation,
                                           creation_physically_connected=creation_connected,
                                           reopened_physically_connected=reopened_connected,
                                           creation_physical_references=creation_peers,
                                           reopened_physical_references=reopened_peers))
            seen.add(connector_id)
    captured_request = pipe['creation_provenance']['creation_request']
    # APS binds the prepared request to the engine-local input model path.
    if (PureWindowsPath(captured_request['DocumentPath']).name.lower() != 'input.rvt'
            or {k: v for k, v in captured_request.items() if k != 'DocumentPath'}
            != {k: v for k, v in requested.items() if k != 'DocumentPath'}):
        raise ValueError('Reopened pipe provenance differs from the staged creation request')
    if any(file_hash(path) != sha256 for path, sha256 in pins.items()):
        raise ValueError('Revit evidence changed during verification')
    return {
        'pipe_unique_id': identifier,
        'pipe_element_id': element_id,
        'authored_rvt_sha256': pins[authored],
        'creation_sha256': pins[creation],
        'inventory_sha256': pins[inventory],
        'write_preparation_sha256': pins[preparation],
        'write_request_sha256': pins[request],
        'reopen_preparation_sha256': pins[reopen_preparation],
        'reopen_request_sha256': pins[reopen_request],
        'tolerance_m': tolerance_m,
        'pipe_matches_capture': True,
        'creation_attribute_matches': attribute_matches,
        'connector_endpoint_error_m': connector_error,
        'connector_endpoint_matches': endpoint_matches,
        'creation_connector_matches': transaction_connectors is not None,
        'creation_connector_readback': sorted(connector_readback, key=lambda row: row['connector_id']),
        'native_execution_authenticated': False,
        'connected_system_verified': False,
        'design_accepted': False,
    }


def add_arguments(parser):
    for name in ('write-stage', 'creation', 'authored', 'inventory', 'reopen-preparation'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--tolerance-m', type=float, required=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    try:
        print(json.dumps(verify(**vars(parser.parse_args())), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f'{error}\n')
