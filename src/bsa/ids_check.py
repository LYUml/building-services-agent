"""Thin adapter around upstream IfcTester CLI; engine exit is not audit success."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from .cli import digest
from .engine import ProjectError


def run(ids,ifc,out):
    paths=[Path(p).resolve() for p in (ids,ifc)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain inputs')
    try:
        version = importlib.metadata.version('ifctester')
        ifc_version = importlib.metadata.version('ifcopenshell')
    except importlib.metadata.PackageNotFoundError as error:
        raise ProjectError('IDS checks require the ids extra: python -m pip install -e ".[ids]"') from error
    if (version, ifc_version) != ('0.8.5', '0.8.5'):
        raise ProjectError('IDS checks require IfcTester 0.8.5 and IfcOpenShell 0.8.5. '
                           'Install the ids extra: python -m pip install -e ".[ids]"')
    before={str(p):digest(p) for p in paths};out.mkdir(parents=True,exist_ok=False)
    report = out / 'ids-report.json'
    log_path = out / 'engine.log'
    command = [sys.executable, '-m', 'ifctester', str(paths[0]), str(paths[1]), '-r', 'Json', '-o', str(report)]
    with log_path.open('wb') as log:
        try:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        except subprocess.TimeoutExpired as error:
            raise ProjectError(f'IfcTester timed out after 120 seconds. Inspect {log_path}') from error
    if process.returncode or not report.is_file():
        raise ProjectError(f'IfcTester engine failed. Inspect {log_path}')
    try:
        audit = json.loads(report.read_text(encoding='utf-8-sig'))
    except ValueError as error:
        raise ProjectError(f'IfcTester returned invalid JSON. Inspect {report} and {log_path}') from error
    if not isinstance(audit, dict) or any(
        type(audit.get(field)) is not int or audit[field] < 0
        for field in ('total_specifications', 'total_checks', 'total_checks_fail')
    ):
        raise ProjectError(f'IfcTester returned invalid audit totals. Inspect {report} and {log_path}')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('IDS/IFC inputs changed')
    result=dict(inputs=before,ifctester_version=version,engine_exit_code=process.returncode,
                calculated_checks_pass=audit.get('status') is True and audit['total_specifications']>0 and audit['total_checks']>0 and audit['total_checks_fail']==0,
                requirements_checked=audit['total_checks'],requirements_failed=audit['total_checks_fail'],
                audit_sha256=digest(report),design_accepted=False,regulatory_compliance='not_established',
                scope='Upstream IDS information requirements only; geometry, engineering physics and regulatory applicability remain separate')
    (out/'ids-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ids');p.add_argument('ifc');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.ids,a.ifc,a.out);print(json.dumps(r,indent=2));return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
