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
    version=importlib.metadata.version('ifctester')
    if version!='0.8.5':raise ProjectError('pinned IfcTester 0.8.5 required')
    before={str(p):digest(p) for p in paths};out.mkdir(parents=True,exist_ok=False)
    with (out/'engine.log').open('wb') as log:
        process=subprocess.run([sys.executable,'-m','ifctester',str(paths[0]),str(paths[1]),'-r','Json','-o',str(out/'ids-report.json')],stdout=log,stderr=subprocess.STDOUT,timeout=120)
    if process.returncode or not (out/'ids-report.json').is_file():raise ProjectError('IfcTester engine failed; inspect engine.log')
    audit=json.loads((out/'ids-report.json').read_text(encoding='utf-8-sig'))
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('IDS/IFC inputs changed')
    result=dict(inputs=before,ifctester_version=version,engine_exit_code=process.returncode,
                calculated_checks_pass=audit.get('status') is True and audit.get('total_specifications',0)>0 and audit.get('total_checks',0)>0,
                requirements_checked=audit.get('total_checks',0),requirements_failed=audit.get('total_checks_fail'),
                audit_sha256=digest(out/'ids-report.json'),design_accepted=False,regulatory_compliance='not_established',
                scope='Upstream IDS information requirements only; geometry, engineering physics and regulatory applicability remain separate')
    (out/'ids-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ids');p.add_argument('ifc');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.ids,a.ifc,a.out);print(json.dumps(r,indent=2));return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
