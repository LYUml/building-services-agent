"""Source-to-execution trial with a shared water/pump/electrical IFC identity."""
import argparse
import json
from pathlib import Path
import shutil

from bsa.cli import digest
from bsa.project_start import start
from bsa.engineering_handoff import run,verify

ROOT=Path(__file__).resolve().parents[1]
FILES=['electrical.json','model.json','network.json','binding.json','catalogue.json','geometry.json','policy.json','pump-curve.json','pump-electrical-link.json','drawing-settings.json']
TASKS=[dict(id='electrical',kind='electrical',project='electrical.json'),
    dict(id='water',kind='network_model_design',project='network.json',model='model.json',binding='binding.json',catalogue='catalogue.json',geometry='geometry.json'),
    dict(id='qa',kind='ifc_clash',depends_on='water',policy='policy.json'),
    dict(id='pump',kind='pump_operating_point',depends_on='water',curve='pump-curve.json'),
    dict(id='coupled',kind='pump_electrical',depends_on='pump',ifc_from='water',project='electrical.json',network_binding='binding.json',link='pump-electrical-link.json',requires_pass=['electrical','qa']),
    dict(id='coupled-qa',kind='ifc_clash',depends_on='coupled',policy='policy.json'),
    dict(id='drawing',kind='ifc_drawing',depends_on='coupled',settings='drawing-settings.json',requires_pass=['coupled-qa']),
    dict(id='review',kind='manual',requires_pass=['electrical','water','qa','pump','coupled','coupled-qa','drawing'],description='Review complete source obligations, real equipment, physical installation, motor protection, native plot and full Hong Kong applicability.')]
MAPPING=[['electrical'],['water'],['qa','coupled-qa'],['pump'],['coupled'],['drawing'],['review']]


def execute(out,wrong_identity=False):
    out=Path(out).resolve();intake=start(ROOT/'examples/engineering-handoff/coupled-brief.md',out)
    if intake['stage_errors']:raise ValueError('Source intake failed')
    transfers={}
    for name in FILES:
        source=ROOT/'examples/water-riser'/name;before=digest(source)
        archived=out/'sources/inputs'/name;archived.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,archived);shutil.copyfile(source,out/name)
        if digest(source)!=before or digest(archived)!=before or digest(out/name)!=before:raise ValueError('Input transfer changed')
        transfers[name]=dict(source=str(source),sha256=before,archived=str(archived.relative_to(out)))
    revision=None
    if wrong_identity:
        path=out/'pump-electrical-link.json';data=json.loads(path.read_text());before=digest(path)
        data['pump_guid']=data['source_port_guid'];data['source']+='; Deliberate negative identity control: a port GUID is not a pump GUID.'
        path.write_text(json.dumps(data,indent=2),encoding='utf-8')
        revision=dict(file=path.name,original_sha256=before,revised_sha256=digest(path),basis='Explicit negative control only; all source originals retained')
    plan=out/'plan.json';source=json.loads(plan.read_text())
    expected=(ROOT/'examples/engineering-handoff/coupled-brief.md').read_text(encoding='utf-8').strip().split('\n\n')
    if [r['quote'] for r in source['requirements']]!=expected or len(expected)!=len(MAPPING):raise ValueError('Authored source interpretation changed')
    bindings={r['id']:dict(tasks=targets,acceptance=r['quote']) for r,targets in zip(source['requirements'],MAPPING)}
    notes={i['id']:'Host interprets the complete quoted obligation with the declared shared-model task graph. Original data transfers '+json.dumps(transfers,sort_keys=True)+'; controlled revision '+json.dumps(revision) for i in source['unresolved_inputs']}
    record=dict(schema='bsa.engineering-handoff/1',source_plan_sha256=digest(plan),tasks=TASKS,requirement_bindings=bindings,interpretation_notes=notes,extra_unresolved_inputs=[])
    review=out/'engineering-review.json';review.write_text(json.dumps(record,indent=2),encoding='utf-8')
    result=run(plan,review,out/'engineering-plan.json',out/'engineering-run')
    checked=verify(out/'engineering-run')
    summary=dict(source_transfers=transfers,controlled_revision=revision,status=result['status'],stages=result['stages'],stage_errors=result['stage_errors'],verification=checked,
        design_accepted=False,scope='Authored synthetic brief, shared water/pump/electrical identity and typed operating scenario; complete engineering pending')
    (out/'demo.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--wrong-pump-identity',action='store_true')
    args=parser.parse_args();r=execute(args.out,args.wrong_pump_identity)
    print(json.dumps({k:r[k] for k in ('status','stage_errors','verification','design_accepted')},indent=2))
