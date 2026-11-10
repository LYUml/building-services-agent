"""Probe the WNTR import boundary in a child process; no model or policy changes."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

from probe_energy_runtime import probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.out.resolve()
    if not output.is_relative_to(root) or output.exists():
        parser.error('Choose a new report file inside this repository')
    try:
        version = importlib.metadata.version('wntr')
    except importlib.metadata.PackageNotFoundError:
        version = None
    attempt = probe([sys.executable, '-c', 'import wntr; print(wntr.__version__)'])
    raw = '\n'.join(str(attempt.get(k, '')) for k in ('stdout', 'stderr', 'error'))
    report = dict(scope='WNTR import only; does not prove EPANET library load, simulation, hydraulic QA or design acceptance',
                  python=sys.executable, installed_wntr_version=version,
                  required_wntr_version='1.5.0', version_matches=version == '1.5.0',
                  import_probe=attempt,
                  explicit_application_control_message='application control policy' in raw.lower(),
                  import_pass=version == '1.5.0' and attempt['launch_pass'],
                  simulation_executed=False, design_accepted=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({k: report[k] for k in ('import_pass', 'explicit_application_control_message', 'simulation_executed')}))
    return 0 if report['import_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
