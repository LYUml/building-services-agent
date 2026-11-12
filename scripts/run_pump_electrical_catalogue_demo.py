"""Public synthetic hydraulic/electrical pump eligibility and full-plan replay."""
import argparse
import copy
import json
from pathlib import Path
import shutil
from bsa import pump_catalogue_iteration as selection,workflow

ROOT=Path(__file__).resolve().parents[1]


def execute(out,control=None):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Fresh project required')
    if control not in (None,'all-electrical-fail','preferred-unknown'):raise ValueError('Declared control required')
    shutil.copytree(ROOT/'examples/water-riser',out)
    curve=out/'pump-curve.json';good=json.loads(curve.read_text());shutil.copyfile(curve,out/'source-pump-curve.json')
    weak=copy.deepcopy(good)
    for row in weak['points']:row['total_pressure_rise_pa']*=.65
    weak['sources'][weak['source']]+=' Explicit insufficient-pressure baseline control; pressure points scaled by 0.65.'
    curve.write_text(json.dumps(weak,indent=2),encoding='utf-8')
    bad=copy.deepcopy(good)
    for point in bad['points']:point['wire_to_water_efficiency']=.02 if point['flow_m3_s'] else 0
    bad['sources'][bad['source']]+=' Explicit synthetic low-efficiency control, not manufacturer data.'
    if control=='preferred-unknown':
        bad['efficiency_basis']='not supplied'
        for point in bad['points']:point.pop('wire_to_water_efficiency')
        bad['sources'][bad['source']]+=' Deliberately absent wire-to-water efficiency; electrical input unknown.'
    rows=[dict(id='preferred',source='Synthetic adverse electrical or missing-efficiency control',preference=0,curve=bad)]
    if control!='all-electrical-fail':rows.append(dict(id='eligible',source='Original synthetic curve, not a real pump product',preference=1,curve=good))
    catalogue=out/'pump-catalogue.json';catalogue.write_text(json.dumps(dict(objective=selection.preference.OBJECTIVE,source='Declared finite synthetic coupled eligibility study',candidates=rows),indent=2),encoding='utf-8')
    plan=out/'coupled-plan.json';workflow.execute(plan,out/'original-run')
    result=selection.run(plan,out/'original-run','pump',catalogue,out/'selected-plan.json',out/'selection',electrical_task='coupled')
    checked=selection.verify(out/'selection')
    summary=dict(status=result['status'],verification=checked,design_accepted=False)
    (out/'demo.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--control',choices=['all-electrical-fail','preferred-unknown']);a=p.parse_args()
    print(json.dumps(execute(a.out,a.control),indent=2))
