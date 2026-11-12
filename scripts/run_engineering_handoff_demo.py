"""Execute a public host-interpreted brief through existing cross-discipline adapters."""
import argparse
import json
from pathlib import Path
import shutil

from bsa.cli import digest
from bsa.project_start import start
from bsa.engineering_handoff import run

ROOT=Path(__file__).resolve().parents[1]
INPUTS={'electrical.json':'examples/office-electrical/project.json',
    'air.json':'examples/network-design/project.json',
    'air-catalogue.json':'examples/network-design/catalogue.json',
    'water.json':'examples/network/water.json','envelopes.json':'examples/mep-ifc/project.json'}
TASKS=[dict(id='electrical',kind='electrical',project='electrical.json'),
    dict(id='air',kind='network_design',project='air.json',catalogue='air-catalogue.json'),
    dict(id='water',kind='network',project='water.json'),
    dict(id='envelopes',kind='bim',project='envelopes.json'),
    dict(id='review',kind='manual',requires_pass=['electrical','air','water','envelopes'],description='Review full source obligations and all pending physical/product/native/regulatory checks.')]


def execute(out,missing_water=False):
    out=Path(out).resolve()
    intake=start(ROOT/'examples/engineering-handoff/brief.md',out)
    if intake['stage_errors']:raise ValueError('Source intake failed: '+str(intake['stage_errors']))
    transfers={}
    for target,name in INPUTS.items():
        source=ROOT/name;before=digest(source);shutil.copyfile(source,out/target)
        if digest(source)!=before or digest(out/target)!=before:raise ValueError('Source transfer changed')
        transfers[target]=dict(source=str(source),sha256=before)
    plan=out/'plan.json';source=json.loads(plan.read_text(encoding='utf-8'))
    passages=(ROOT/'examples/engineering-handoff/brief.md').read_text(encoding='utf-8').strip().split('\n\n')
    if [r['quote'] for r in source['requirements']]!=passages:raise ValueError('Authored host interpretation no longer matches all original passages')
    bindings={r['id']:dict(tasks=[task['id']],acceptance=r['quote']) for r,task in zip(source['requirements'],TASKS)}
    notes={i['id']:'Host interpretation binds the complete original passage to '+bindings[next(r['id'] for r in source['requirements'] if r['task'] in i['blocks_tasks'])]['tasks'][0]+'. All supplied JSON inputs retain explicit synthetic source classifications; source transfers: '+json.dumps(transfers,sort_keys=True) for i in source['unresolved_inputs']}
    gaps=[]
    if missing_water:
        r=source['requirements'][2]
        gaps=[dict(id='water-property-review',kind='missing',description='Controlled unresolved review of supplied water-property applicability; do not assume approval.',sources=[dict(passage=r['passage'],quote=r['quote'])],blocks_tasks=['water'])]
    record=dict(schema='bsa.engineering-handoff/1',source_plan_sha256=digest(plan),tasks=TASKS,
        requirement_bindings=bindings,interpretation_notes=notes,extra_unresolved_inputs=gaps)
    review=out/'engineering-review.json';review.write_text(json.dumps(record,indent=2),encoding='utf-8')
    result=run(plan,review,out/'engineering-plan.json',out/'engineering-run')
    summary=dict(source_transfers=transfers,status=result['status'],stages=result['stages'],stage_errors=result['stage_errors'],
        original_requirements=len(source['requirements']),design_accepted=False,
        scope='Explicit authored host interpretation, independent synthetic disciplines and standalone BIM; no semantic generalisation or integrated installation acceptance')
    (out/'demo.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--missing-water',action='store_true')
    args=parser.parse_args();print(json.dumps(execute(args.out,args.missing_water),indent=2))
