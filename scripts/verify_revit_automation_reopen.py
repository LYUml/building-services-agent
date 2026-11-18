"""Reconcile a Revit creation receipt with a separately collected saved inventory."""
import argparse
import json
from pathlib import Path, PureWindowsPath

from bsa import workspace
from bsa.revit_connectivity import reconstruct
from bsa.source_refs import file_hash


def verify(write_stage, creation, authored, inventory, reopen_preparation, tolerance_m):
    stage, creation, authored, inventory, reopen_preparation = (
        Path(path).resolve() for path in (write_stage, creation, authored, inventory, reopen_preparation))
    request = stage / 'pipe-request.json'
    preparation = stage / 'preparation.json'
    if not all(workspace.allowed(path) for path in (request, preparation, creation, authored, inventory, reopen_preparation)):
        raise ValueError('Use files from the selected project workspace')
    paths = (request, preparation, creation, authored, inventory, reopen_preparation)
    pins = {path: file_hash(path) for path in paths}
    prepared, created, requested, reopened = (
        json.loads(path.read_bytes()) for path in (preparation, creation, request, inventory))
    if (prepared['operation'] != 'create-pipe'
            or pins[request] != prepared['request_sha256']
            or created['request_sha256'] != pins[request]
            or created['input_rvt_sha256'] != prepared['saved_rvt_sha256']
            or requested['SavedRvtSha256'] != prepared['saved_rvt_sha256']
            or created['adapter_sha256'] != prepared['assembly_sha256']
            or created['saved_rvt_sha256'] != pins[authored]):
        raise ValueError('Creation evidence does not match the prepared request and saved RVT')

    checked = reconstruct(inventory, authored, tolerance_m, automation_receipt=reopen_preparation)
    identifier = created['transaction_result']['unique_id']
    pipes = [pipe for pipe in reopened['pipes'] if pipe['unique_id'] == identifier]
    revisions = [row for row in checked['revision_checks'] if row['owner'] == identifier]
    if len(pipes) != 1 or len(revisions) != 1 or revisions[0]['status'] != 'consistent':
        raise ValueError('Reopened pipe identity or geometry does not match the transaction')
    captured_request = pipes[0]['creation_provenance']['creation_request']
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
        'pipe_matches_capture': True,
        'native_execution_authenticated': False,
        'connected_system_verified': False,
        'design_accepted': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('write-stage', 'creation', 'authored', 'inventory', 'reopen-preparation'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--tolerance-m', type=float, required=True)
    try:
        print(json.dumps(verify(**vars(parser.parse_args())), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f'{error}\n')
