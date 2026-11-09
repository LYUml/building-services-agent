"""Synthetic native rectangular supply-flow denominator binding to the HK base fan rule."""
import copy
import json
from pathlib import Path
import shutil
import argparse
from bsa.cli import digest
from bsa.workflow import execute
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


def run(out,sources):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('new repository-local output required')
    out.mkdir(parents=True);ex=ROOT/'examples/rectangular-air'
    for name in ('undersized-wall.json','binding.json','wall-options.json'):shutil.copyfile(ex/name,out/name)
    project=json.loads((ex/'binding-project.json').read_text());project['nodes'][1]['demand_m3_s']=2.
    (out/'project.json').write_text(json.dumps(project,indent=2),encoding='utf-8')
    catalog=json.loads((ex/'single-catalogue.json').read_text())
    next(r for r in catalog['options'] if r['id']=='large').update(width_m=1.,height_m=.5)
    (out/'catalogue.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    shutil.copyfile(ROOT/'regulations/hk/fan-power-2026.11.10/pack.json',out/'fan-pack.json');cache=out/'sources';cache.mkdir()
    for name in ('emsd-bec-2024.pdf','emsd-tg-bec-2024.pdf'):shutil.copyfile(Path(sources)/name,cache/name)
    base=json.loads((ROOT/'examples/hk-fan-power/project.json').read_text());base['facts'].pop('supply_design_airflow')
    base['facts']['network_represents_supply_design_flow']=dict(value=True,source='Explicit synthetic whole-supply correspondence; not a verified real building inventory')
    tasks=[dict(id='model',kind='rectangular_model_design',project='project.json',model='undersized-wall.json',binding='binding.json',catalogue='catalogue.json',geometry='wall-options.json')]
    paragraphs=['Size, regenerate and natively verify the explicitly synthetic 2 m3/s straight rectangular supply network. Preserve source assumptions, endpoints, identities and pending full acceptance.']
    requirements=[dict(id='R1',passage='P001',quote=paragraphs[0],task='model',acceptance='Actual saved native and numerical correspondence; not full HVAC design')]
    for index,label in enumerate(('pass','exceeded','unknown-supply'),2):
        basis=copy.deepcopy(base)
        if label=='exceeded':basis['facts']['fan_motor_power']['value']=3201.
        if label=='unknown-supply':basis['facts']['network_represents_supply_design_flow']['value']=None
        (out/(label+'.json')).write_text(json.dumps(basis,indent=2),encoding='utf-8')
        text='Evaluate the synthetic '+label+' motor-power basis using the exact native supply-network flow, retaining unresolved correspondence and independent engineering review.';paragraphs.append(text)
        tasks.extend([dict(id=label,kind='rectangular_fan_regulations',depends_on='model',basis=label+'.json',pack='fan-pack.json',sources='sources'),dict(id=label+'-review',kind='manual',requires_pass=[label],description='Real fan inventory/electrical operating point, scope, controls and full acceptance pending')])
        for suffix in ('','-review'):requirements.append(dict(id='R'+str(index)+suffix,passage=f'P{index:03}',quote=text,task=label+suffix,acceptance='Scoped native-flow rule correspondence and preserved review gates only'))
    brief=out/'brief.md';brief.write_text('\n\n'.join(paragraphs)+'\n',encoding='utf-8')
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={f'P{i:03}':'requirement' for i in range(1,5)},tasks=tasks,requirements=requirements)
    path=out/'plan.json';path.write_text(json.dumps(plan,indent=2),encoding='utf-8');execute(path,out/'workflow');d=diagnose(path,out/'workflow')
    states={t['id']:t['status'] for t in d['tasks']}
    if [states[k] for k in ('model','pass','exceeded','unknown-supply')]!=['pass','pass','fail','pending']:raise ValueError('unexpected native fan-rule demonstration states')
    (out/'demonstration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');return d


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--sources',type=Path,required=True)
    r=run(**vars(parser.parse_args()));print(json.dumps({t['id']:t['status'] for t in r['tasks']}))
