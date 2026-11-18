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
    transaction = created['transaction_result']
    identifier = transaction['unique_id']
    pipes = [pipe for pipe in reopened['pipes'] if pipe['unique_id'] == identifier]
    revisions = [row for row in checked['revision_checks'] if row['owner'] == identifier]
    if len(pipes) != 1 or len(revisions) != 1 or revisions[0]['status'] != 'consistent':
        raise ValueError('Reopened pipe identity or geometry does not match the transaction')
    for issue in checked['issues']:
        endpoints = (issue.get('port', (None,)), issue.get('target', (None,)))
        if any(port[0] == identifier for port in endpoints):
            raise ValueError(f"Reopened pipe has inconsistent connector evidence: {', '.join(issue['reasons'])}")
    pipe = pipes[0]
    for field in ('diameter_m', 'length_m'):
        recorded = transaction.get(field)
        if (type(recorded) not in (int, float) or not math.isfinite(recorded)
                or recorded <= 0 or abs(recorded - pipe[field]) > tolerance_m):
            raise ValueError(f'Reopened pipe {field} differs from the creation readback')
    if transaction.get('source') != requested['Source']:
        raise ValueError('Creation readback source differs from the staged request')
    connectors = pipe['connectors']
    if (transaction.get('connector_count') != 2 or len(connectors) != 2
            or any(c['domain'] != 'DomainPiping' or c['connector_type'] != 'End' for c in connectors)):
        raise ValueError('Reopened pipe must retain two piping end connectors')
    origins = [connector['origin_m'] for connector in connectors]
    endpoints = pipe['endpoints_m']
    connector_error = min(
        max(math.dist(origin, endpoint) for origin, endpoint in zip(order, endpoints, strict=True))
        for order in (origins, origins[::-1])
    )
    if origins[0] == origins[1] or connector_error > tolerance_m:
        raise ValueError('Reopened pipe connector origins do not match distinct curve endpoints')
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
        'authored_rvt_sha256': pins[authored],
        'creation_sha256': pins[creation],
        'inventory_sha256': pins[inventory],
        'reopen_request_sha256': pins[reopen_request],
        'pipe_matches_capture': True,
        'connector_endpoint_error_m': connector_error,
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
