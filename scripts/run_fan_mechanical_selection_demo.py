"""Synthetic mechanical-aware curve ranking against a real pinned speed table."""
import argparse
import copy
import json
from pathlib import Path
import shutil
from bsa.workflow import execute
ROOT=Path(__file__).resolve().parents[1]


def stage(out,pdf,label):
    ex=ROOT/'examples/rectangular-air';out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('new repository-local output required')
    out.mkdir(parents=True)
    for p in ex.glob('*.json'):shutil.copyfile(p,out/p.name)
    shutil.copyfile(ex/'brief.md',out/'brief.md');shutil.copyfile(ROOT/'sources/products/tcf-bc-sw-122.json',out/'product.json');shutil.copyfile(pdf,out/'manufacturer.pdf')
    catalogue=json.loads((out/'fan-catalogue.json').read_text());good=catalogue['candidates'][-1]
    first=copy.deepcopy(good);first.update(id='first',preference=0,source='Synthetic curve/class association for ranking tests; not manufacturer curve data')
    second=copy.deepcopy(first);second.update(id='second',preference=1)
    first['curve']['speed_rpm']=3500;second['curve']['speed_rpm']=1450
    classes={'first':'Class_I','second':'Class_I'}
    if label=='preferred-unknown':classes['first']=None
    if label=='lower-unknown':
        first['curve']['speed_rpm']=1450;second['curve']['speed_rpm']=3500;classes['second']=None
    if label=='all-overspeed':second['curve']['speed_rpm']=3500
    catalogue['candidates']=[first,second]
    catalogue['mechanical']=dict(record='product.json',pdf='manufacturer.pdf',classes={id:dict(product_reference='BC-SW 122',construction_class=value,source='Synthetic declared class association; actual product identity unverified') for id,value in classes.items()})
    (out/'fan-catalogue.json').write_text(json.dumps(catalogue,indent=2))
    return out/'fan-selected-plan.json'


def run(out,pdf):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('new repository-local output required')
    out.mkdir(parents=True);result={}
    for label in ('overspeed-first','preferred-unknown','lower-unknown','all-overspeed'):
        root=out/label;plan=stage(root,pdf,label);r=execute(plan,root/'workflow')
        selection=json.loads((root/'workflow/fan/fan-selection.json').read_text())
        expected={'overspeed-first':'pass','preferred-unknown':'pending','lower-unknown':'pass','all-overspeed':'fail'}[label]
        if r['tasks']['fan']['status']!=expected:raise ValueError('unexpected mechanical-aware ranking status')
        if expected=='pass' and r['tasks']['selected-operation']['status']!='pass':raise ValueError('selected handoff failed')
        if expected!='pass' and (root/'workflow/selected-operation').exists():raise ValueError('unresolved selection invoked consumer')
        result[label]=dict(states={k:v['status'] for k,v in r['tasks'].items()},selected=selection['selected']['id'] if selection['selected'] else None,unresolved_preference=selection['unresolved_preference'])
    report=dict(cases=result,design_accepted=False,scope='Real speed table; synthetic curves/product associations only')
    (out/'demonstration.json').write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--pdf',type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args()))))
