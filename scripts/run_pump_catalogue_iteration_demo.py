"""Public synthetic finite pump ranking followed by full coupled-plan replay."""
import argparse
import json
from pathlib import Path
import shutil
from bsa import pump_catalogue_iteration as selection,workflow

ROOT=Path(__file__).resolve().parents[1]


def execute(out,no_eligible=False):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Fresh project required')
    shutil.copytree(ROOT/'examples/water-riser',out)
    curve=out/'pump-curve.json';good=json.loads(curve.read_text())
    shutil.copyfile(curve,out/'source-pump-curve.json')
    weak=json.loads(curve.read_text())
    for row in weak['points']:row['total_pressure_rise_pa']*=.65
    weak['sources'][weak['source']]+=' Explicit insufficient-pressure control: original pressures multiplied by 0.65, not a real product.'
    curve.write_text(json.dumps(weak,indent=2),encoding='utf-8')
    rows=[dict(id='insufficient',source='Declared synthetic insufficient-pressure candidate',preference=0,curve=weak)]
    if not no_eligible:rows.append(dict(id='eligible',source='Original declared synthetic example curve, not a manufacturer product',preference=1,curve=good))
    catalogue=out/'pump-catalogue.json';catalogue.write_text(json.dumps(dict(objective=selection.preference.OBJECTIVE,source='Public synthetic finite candidate comparison; real equipment unresolved',candidates=rows),indent=2),encoding='utf-8')
    plan=out/'coupled-plan.json';workflow.execute(plan,out/'original-run')
    result=selection.run(plan,out/'original-run','pump',catalogue,out/'selected-plan.json',out/'selection')
    checked=selection.verify(out/'selection')
    summary=dict(status=result['status'],verification=checked,design_accepted=False)
    (out/'demo.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--no-eligible',action='store_true');a=p.parse_args()
    print(json.dumps(execute(a.out,a.no_eligible),indent=2))
