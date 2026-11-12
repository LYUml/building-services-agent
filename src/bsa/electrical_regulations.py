"""Run original electrical sources through path calculation and jurisdiction checks."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .electrical_paths import run as run_paths, bind_facts
from .regulations import evaluate, source_paths
from . import electrical_paths,regulations,engine


def run(project,topology,basis,pack,sources,out):
    files=[Path(p).resolve() for p in (project,topology,basis,pack)]
    out=Path(out).resolve()
    before={str(p):digest(p) for p in files}
    before.update({str(Path(p).resolve()):digest(Path(p)) for p in (__file__,electrical_paths.__file__,regulations.__file__,engine.__file__)})
    data=json.loads(files[3].read_text(encoding='utf-8-sig'))
    official=source_paths(data,sources)
    if any(out==p or out in p.parents for p in set(files)|official):
        raise ProjectError('output must not contain calculation or official sources')
    cached={str(p):digest(p) if p.is_file() else None for p in official}
    if out.exists():raise ProjectError('refusing to overwrite electrical regulation run')
    calculation=run_paths(*files[:3],out/'calculation')
    report=out/'calculation/electrical-paths.json'
    # Bind from this invocation's in-memory calculation, never a supplied result JSON.
    bound=bind_facts(calculation,json.loads(files[2].read_text(encoding='utf-8-sig')),str(report)+' SHA256 '+digest(report))
    checks={key:evaluate(data,value,sources) for key,value in bound.items()}
    branch_pass=calculation['branch_calculation']['calculated_checks_pass']
    rules_pass=bool(checks) and all(c['supported_checks_pass'] for c in checks.values())
    status='fail' if not branch_pass else ('pass' if rules_pass else 'pending')
    if any(digest(Path(p))!=h for p,h in before.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in cached.items()):
        raise ProjectError('electrical regulation source changed during execution')
    before.update({p:h for p,h in cached.items() if h is not None})
    result=dict(inputs=before,inputs_unchanged=True,missing_sources=[p for p,h in cached.items() if h is None],
                calculation_sha256=digest(report),circuit_checks=checks,branch_checks_pass=branch_pass,
                supported_regulation_checks_pass=rules_pass,status=status,design_accepted=False,
                regulatory_compliance='not_established',
                scope='Fresh single-phase radial calculation and selected per-circuit rules; passing voltage drop cannot clear failed branch checks',
                pending=calculation['pending'])
    (out/'electrical-regulation-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for key in ('topology','basis','pack','sources','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.topology,a.basis,a.pack,a.sources,a.out)
    return 0 if r['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())
