"""Stage explicitly synthetic fact cases against pinned official fan-power sources."""
import argparse
import copy
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.workflow import execute
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


def run(out,sources):
    out=Path(out).resolve();sources=Path(sources).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('new repository-local output required')
    out.mkdir(parents=True);shutil.copyfile(ROOT/'regulations/hk/fan-power-2026.11.10/pack.json',out/'pack.json')
    cache=out/'sources';cache.mkdir()
    for name in ('emsd-bec-2024.pdf','emsd-tg-bec-2024.pdf'):shutil.copyfile(sources/name,cache/name)
    base=json.loads((ROOT/'examples/hk-fan-power/project.json').read_text());tasks=[];requirements=[];paragraphs=[]
    for index,label in enumerate(('pass','exceeded','missing-power','exempt','adjustment'),1):
        p=copy.deepcopy(base)
        if label=='exceeded':p['facts']['fan_motor_power']['value']=3201.
        if label=='missing-power':p['facts'].pop('fan_motor_power')
        if label=='exempt':p['facts']['fan_motor_power']['value']=2499.
        if label=='adjustment':p['facts']['clean_treatment_pressure_drop']['value']=251.
        (out/(label+'.json')).write_text(json.dumps(p,indent=2),encoding='utf-8')
        text='Evaluate the explicitly synthetic '+label+' fan-power facts against the selected base rule, retaining missing/exempt/adjustment and full engineering review separately.'
        paragraphs.append(text);tasks.extend([dict(id=label,kind='regulations',project=label+'.json',pack='pack.json',sources='sources'),dict(id=label+'-review',kind='manual',requires_pass=[label],description='Actual applicability, clean motor power/inventory, controls and full acceptance remain pending')])
        for suffix in ('','-review'):requirements.append(dict(id='R'+str(index)+suffix,passage=f'P{index:03}',quote=text,task=label+suffix,acceptance='Source-pinned conditional rule/gate evidence only; not equipment selection or whole-project conformity'))
    brief=out/'brief.md';brief.write_text('\n\n'.join(paragraphs)+'\n',encoding='utf-8')
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={f'P{i:03}':'requirement' for i in range(1,6)},tasks=tasks,requirements=requirements)
    path=out/'plan.json';path.write_text(json.dumps(plan,indent=2),encoding='utf-8');execute(path,out/'workflow');diagnosis=diagnose(path,out/'workflow')
    expected=['pass','review_required','pending','not_applicable','pending'];rows={}
    for label,status in zip(('pass','exceeded','missing-power','exempt','adjustment'),expected):
        row=json.loads((out/'workflow'/label/'regulation-checks.json').read_text())['checks'][0]
        if row['status']!=status:raise ValueError('unexpected fan-power case: '+label)
        rows[label]=row
    result=dict(checks=rows,tasks=diagnosis['tasks'],integrity_pass=True,design_accepted=False,scope='Synthetic sourced-fact rule and downstream-gate demonstration; no native fan/network binding or full acceptance')
    (out/'demonstration.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--sources',type=Path,required=True)
    r=run(**vars(parser.parse_args()));print(json.dumps({k:v['status'] for k,v in r['checks'].items()}))
