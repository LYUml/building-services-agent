"""Explicit synthetic pump-curve revision through the unchanged coupled workflow."""
import argparse
import json
from pathlib import Path
import shutil

from bsa import catalogue_iteration as iteration,workflow
from bsa.catalogue_iteration_verify import verify
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


def execute(out,still_weak=False):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Fresh project required')
    shutil.copytree(ROOT/'examples/water-riser',out)
    original=out/'pump-curve.json'
    shutil.copyfile(original,out/'source-pump-curve.json')
    curve=json.loads(original.read_text())
    for point in curve['points']:point['total_pressure_rise_pa']*=.65
    curve['sources'][curve['source']]+=' Explicit synthetic insufficient-pressure control: original pressure-rise points multiplied by 0.65; no actual product.'
    original.write_text(json.dumps(curve,indent=2),encoding='utf-8')
    replacement=out/'revised-pump-curve.json'
    if still_weak:
        other=json.loads(original.read_text());other['sources'][other['source']]+=' Explicit alternative still-insufficient control.'
        replacement.write_text(json.dumps(other,indent=2),encoding='utf-8')
    else:shutil.copyfile(out/'source-pump-curve.json',replacement)
    plan=out/'coupled-plan.json';before={p.name:digest(p) for p in (plan,original,replacement)}
    workflow.execute(plan,out/'original-run')
    result=iteration.run(plan,out/'original-run','pump',replacement,out/'revised-plan.json',out/'iteration')
    checked=verify(out/'iteration')
    assert all(digest(out/name)==sha for name,sha in before.items())
    summary=dict(status=result['status'],stages=result['stages'],stage_errors=result['stage_errors'],verification=checked,
        source_snapshots=before,design_accepted=False,
        scope='Explicit synthetic curve revision only; unchanged full coupled plan, not automatic catalogue discovery or product approval')
    (out/'demo.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--still-weak',action='store_true')
    a=p.parse_args();print(json.dumps(execute(a.out,a.still_weak),indent=2))
