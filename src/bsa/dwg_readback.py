"""Run the optional ACadSharp worker for source-bound DWG inventory."""
from collections import Counter
import json
import os
from pathlib import Path
import subprocess

from . import workspace
from .source_refs import file_hash


def host_file(name):
    path = Path(os.environ.get(name, ''))
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f'Set {name} to an absolute host runtime file')
    return path.resolve()


def run(source, out):
    source, out = (Path(path).resolve() for path in (source, out))
    if not workspace.allowed(source) or not source.is_file() or source.suffix.lower() != '.dwg':
        raise ValueError('Select an existing DWG in the permitted workspace')
    if not workspace.intake_output(out) or out.exists() or out.suffix.lower() != '.json':
        raise ValueError('Use a fresh JSON report in the permitted workspace')
    dotnet = host_file('BSA_ACADSHARP_DOTNET')
    worker = host_file('BSA_ACADSHARP_WORKER')
    source_hash, worker_hash = file_hash(source), file_hash(worker)
    completed = subprocess.run([str(dotnet), str(worker), str(source)], cwd=worker.parent,
                               capture_output=True, encoding='utf-8', timeout=120)
    if completed.returncode:
        raise ValueError(f'ACadSharp DWG reader failed (exit {completed.returncode}): {completed.stderr[:1000].strip()}')
    result = json.loads(completed.stdout)
    if (not isinstance(result, dict) or result.get('schema') != 'bsa.acadsharp-modelspace/1'
            or result.get('source_sha256') != source_hash or result.get('reader_version') != '3.8.35'
            or result.get('native_autocad_executed') is not False or result.get('design_accepted') is not False
            or not isinstance(result.get('entities'), list)):
        raise ValueError('ACadSharp report identity or scope differs from the selected input')
    entities = result['entities']
    if any(not isinstance(row, dict) or set(row) != {'handle', 'type', 'layer', 'geometry'}
           or not all(isinstance(row[k], str) and row[k] for k in ('handle', 'type', 'layer'))
           for row in entities) or len({row['handle'] for row in entities}) != len(entities):
        raise ValueError('ACadSharp entity inventory has invalid or duplicate identities')
    result['worker_sha256'] = worker_hash
    report = json.dumps(result, indent=2, allow_nan=False)
    if file_hash(source) != source_hash or file_hash(worker) != worker_hash:
        raise ValueError('DWG or ACadSharp worker changed during inventory')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        stream.write(report)
    return dict(report=str(out), report_sha256=file_hash(out), source_sha256=source_hash,
                entity_count=len(entities), counts=dict(sorted(Counter(row['type'] for row in entities).items())),
                native_autocad_executed=False, design_accepted=False)
