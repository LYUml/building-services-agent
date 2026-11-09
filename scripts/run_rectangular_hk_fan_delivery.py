"""Compose native rectangular sizing, HK fan-rule, coordination and guarded drawing release."""
import argparse
import json
from pathlib import Path
import shutil
from run_rectangular_hk_fan_demo import stage,ROOT
from bsa.cli import digest
from bsa.workflow import execute
from bsa.workflow_status import diagnose


def run(out,sources,autocad=None,elbow=False):
    path=stage(out,sources);out=path.parent;plan=json.loads(path.read_text());example=ROOT/'examples/rectangular-air'
    if elbow:
        for name in ('elbow-chain-model.json','elbow-chain-binding.json','elbow-chain-clash-policy.json','drawing-settings.json','elbow-sheet-settings.json'):
            shutil.copyfile(example/name,out/name)
        project=json.loads((example/'elbow-chain-project.json').read_text())
        project['nodes'][1]['demand_m3_s']=2.
        project['segments'][0]['max_velocity_m_s']=15.
        project['sources']['demo']+=' Synthetic 2 m3/s and 15 m/s velocity target for gate testing only; not a design recommendation.'
        (out/'project.json').write_text(json.dumps(project,indent=2),encoding='utf-8')
        plan['tasks'][0]=dict(id='model',kind='rectangular_network_binding',project='project.json',model='elbow-chain-model.json',binding='elbow-chain-binding.json')
        policy='elbow-chain-clash-policy.json';sheet='elbow-sheet-settings.json'
    else:
        model_path=out/'undersized-wall.json';model=json.loads(model_path.read_text())
        context=json.loads((example/'clearance-wall.json').read_text())
        model['sources']['equipment']=context['sources']['equipment'];device=context['devices'][-1];device['origin_m'][1]=2.
        model['devices'].append(device);model_path.write_text(json.dumps(model,indent=2),encoding='utf-8')
        for name in ('clash-policy.json','drawing-settings.json','sheet-settings.json'):shutil.copyfile(example/name,out/name)
        policy='clash-policy.json';sheet='sheet-settings.json'
    paragraphs=(out/'brief.md').read_text().strip().split('\n\n')
    if elbow:paragraphs[0]='Natively verify the explicitly synthetic fixed-section 2 m3/s lead/quarter/tail rectangular supply chain, with true arc length and separately assumed per-piece excess K. No automatic bend resizing or product selection.'
    paragraphs[0]+=' Check every represented synthetic element for overlap and declared clearance before drawing.'
    for i in range(1,4):paragraphs[i]+=' Release a native outer-envelope sheet only after the same-model rule and coordination pass; keep full engineering and visual review separate.'
    for requirement in plan['requirements']:requirement['quote']=paragraphs[int(requirement['passage'][1:])-1]
    tasks=[plan['tasks'][0],dict(id='coordination',kind='ifc_clash',depends_on='model',policy=policy)]
    plan['requirements'].append(dict(id='R-coordination',passage='P001',quote=paragraphs[0],task='coordination',acceptance='Actual selected-model represented geometry checks only; not whole-building context/product validation'))
    for i,label in enumerate(('pass','exceeded','unknown-supply'),2):
        rule=next(t for t in plan['tasks'] if t['id']==label);review=next(t for t in plan['tasks'] if t['id']==label+'-review')
        drawing=label+'-drawing';review['requires_pass']=[label,'coordination',drawing]
        tasks.extend([rule,dict(id=drawing,kind='rectangular_drawing',depends_on='model',requires_pass=['coordination',label],settings='drawing-settings.json',sheet=sheet),review])
        plan['requirements'].append(dict(id='R'+str(i)+'-drawing',passage=f'P{i:03}',quote=paragraphs[i-1],task=drawing,acceptance='Same-producer rule and clash gates, saved/native DXF audits, DWG reopening and physical PDF scale; actual visual/engineering review remains separate'))
    plan['tasks']=tasks;brief=out/'brief.md';brief.write_text('\n\n'.join(paragraphs)+'\n',encoding='utf-8');plan['brief_sha256']=digest(brief)
    path.write_text(json.dumps(plan,indent=2),encoding='utf-8');execute(path,out/'workflow',autocad=autocad);d=diagnose(path,out/'workflow')
    states={t['id']:t for t in d['tasks']}
    if states['model']['status']!='pass' or states['coordination']['status']!='pass':raise ValueError('unexpected physical/numerical case failure')
    if states['pass-drawing']['status']!=('pass' if autocad else 'pending'):raise ValueError('unexpected positive drawing status')
    for label in ('exceeded','unknown-supply'):
        if states[label+'-drawing']['status']!='pending' or (out/'workflow'/(label+'-drawing')).exists() or 'required checks unresolved' not in states[label+'-drawing']['recorded_scope']:raise ValueError('nonpassing rule did not block drawing adapter')
    result=dict(tasks=d['tasks'],integrity_pass=True,design_accepted=False,scope='Synthetic complete scoped composition; fan electrical evidence, inventory authenticity, controls and full HVAC/installation acceptance remain pending')
    (out/'demonstration.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--sources',type=Path,required=True);parser.add_argument('--autocad',type=Path);parser.add_argument('--elbow',action='store_true')
    r=run(**vars(parser.parse_args()));print(json.dumps({t['id']:t['status'] for t in r['tasks']}))
