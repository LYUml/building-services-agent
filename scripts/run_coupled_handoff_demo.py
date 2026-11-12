"""Source-to-execution trial with a shared water/pump/electrical IFC identity."""
import argparse
import copy
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


def execute(out,wrong_identity=False,*,native=False,autocad=None,hk_sources=None,hk_control=None):
    if autocad is not None and not native:raise ValueError('Native scope must be explicit when supplying AutoCAD')
    if hk_control not in (None,'long-feeder','unknown-scope') or hk_control is not None and hk_sources is None:raise ValueError('HK controls require explicit official sources')
    out=Path(out).resolve();supplement=ROOT/'examples/engineering-handoff/coupled-native-brief.md';hk_brief=ROOT/'examples/engineering-handoff/coupled-hk-brief.md'
    supplements=([supplement] if native else [])+([hk_brief] if hk_sources is not None else [])
    official=None
    if hk_sources is not None:
        pack_path=ROOT/'regulations/hk/2026.11.08/pack.json';pack=json.loads(pack_path.read_text())
        official=Path(hk_sources).resolve()/pack['sources']['emsd_wiring_2025']['cache_filename']
        if not official.is_file() or digest(official)!=pack['sources']['emsd_wiring_2025']['sha256']:raise ValueError('Pinned official EMSD source required before intake')
    intake=start(ROOT/'examples/engineering-handoff/coupled-brief.md',out,supplements=supplements)
    if intake['stage_errors']:raise ValueError('Source intake failed')
    transfers={}
    for name in FILES+(['native-sheet.json'] if native else []):
        source=ROOT/'examples/water-riser'/name;before=digest(source)
        archived=out/'sources/inputs'/name;archived.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,archived);shutil.copyfile(source,out/name)
        if digest(source)!=before or digest(archived)!=before or digest(out/name)!=before:raise ValueError('Input transfer changed')
        transfers[name]=dict(source=str(source),sha256=before,archived=str(archived.relative_to(out)))
    hk_revision=None
    if official is not None:
        for src,name in [(ROOT/'examples/engineering-handoff/hk-electrical-topology.json','hk-electrical-topology.json'),(ROOT/'examples/engineering-handoff/hk-electrical-basis.json','hk-electrical-basis.json'),(pack_path,'hk-voltage-drop-pack.json')]:
            archived=out/'sources/inputs'/name;shutil.copyfile(src,archived);shutil.copyfile(src,out/name)
            transfers[name]=dict(source=str(src),sha256=digest(src),archived=str(archived.relative_to(out)))
        (out/'hk-sources').mkdir();shutil.copyfile(official,out/'hk-sources'/official.name)
        if digest(out/'hk-sources'/official.name)!=digest(official):raise ValueError('Official source transfer changed')
        if hk_control:
            name='hk-electrical-topology.json' if hk_control=='long-feeder' else 'hk-electrical-basis.json'
            path=out/name;data=json.loads(path.read_text());before=digest(path)
            if hk_control=='long-feeder':
                feeder=data['radials']['L1']['feeders'][0];feeder['route_length_m']=1000;feeder['source']='Explicit negative synthetic 1000 m feeder control, not a measured route; original project/branch/hardware targets unchanged.'
            else:data['facts'].pop('fixed_current_using_equipment')
            path.write_text(json.dumps(data,indent=2),encoding='utf-8')
            hk_revision=dict(control=hk_control,file=name,original_sha256=before,revised_sha256=digest(path))
    revision=None
    if wrong_identity:
        path=out/'pump-electrical-link.json';data=json.loads(path.read_text());before=digest(path)
        data['pump_guid']=data['source_port_guid'];data['source']+='; Deliberate negative identity control: a port GUID is not a pump GUID.'
        path.write_text(json.dumps(data,indent=2),encoding='utf-8')
        revision=dict(file=path.name,original_sha256=before,revised_sha256=digest(path),basis='Explicit negative control only; all source originals retained')
    plan=out/'plan.json';source=json.loads(plan.read_text())
    expected=(ROOT/'examples/engineering-handoff/coupled-brief.md').read_text(encoding='utf-8').strip().split('\n\n')
    tasks=copy.deepcopy(TASKS);mapping=copy.deepcopy(MAPPING)
    if native:
        expected+=supplement.read_text(encoding='utf-8').strip().split('\n\n')
        mapping+=[['native'],['native','review']]
        tasks.insert(-1,dict(id='native',kind='ifc_native',depends_on='drawing',settings='native-sheet.json',requires_pass=['coupled-qa']))
        tasks[-1]['requires_pass'].append('native')
    if official is not None:
        expected+=hk_brief.read_text(encoding='utf-8').strip().split('\n\n');mapping+=[['hk-rules'],['hk-rules','review']]
        tasks.insert(1,dict(id='hk-rules',kind='electrical_regulations',project='electrical.json',topology='hk-electrical-topology.json',basis='hk-electrical-basis.json',pack='hk-voltage-drop-pack.json',sources='hk-sources',requires_pass=['electrical']))
        next(t for t in tasks if t['id']=='coupled')['requires_pass'].append('hk-rules')
        tasks[-1]['requires_pass'].append('hk-rules')
    if [r['quote'] for r in source['requirements']]!=expected or len(expected)!=len(mapping):raise ValueError('Authored source interpretation changed')
    bindings={r['id']:dict(tasks=targets,acceptance=r['quote']) for r,targets in zip(source['requirements'],mapping)}
    notes={i['id']:'Host interprets the complete quoted obligation with the declared shared-model task graph. Original data transfers '+json.dumps(transfers,sort_keys=True)+'; controlled revision '+json.dumps(revision)+'; scoped HK control '+json.dumps(hk_revision) for i in source['unresolved_inputs']}
    record=dict(schema='bsa.engineering-handoff/1',source_plan_sha256=digest(plan),tasks=tasks,requirement_bindings=bindings,interpretation_notes=notes,extra_unresolved_inputs=[])
    review=out/'engineering-review.json';review.write_text(json.dumps(record,indent=2),encoding='utf-8')
    result=run(plan,review,out/'engineering-plan.json',out/'engineering-run',execute_options={'autocad':autocad} if autocad is not None else None)
    checked=verify(out/'engineering-run')
    summary=dict(source_transfers=transfers,controlled_revision=revision,hk_revision=hk_revision,official_source=dict(path=str(official),sha256=digest(official)) if official is not None else None,native_requested=native,status=result['status'],stages=result['stages'],stage_errors=result['stage_errors'],verification=checked,
        design_accepted=False,scope='Authored synthetic brief, shared water/pump/electrical identity and typed operating scenario; complete engineering pending')
    (out/'demo.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--wrong-pump-identity',action='store_true');parser.add_argument('--native',action='store_true');parser.add_argument('--autocad');parser.add_argument('--hk-sources');parser.add_argument('--hk-control',choices=['long-feeder','unknown-scope'])
    args=parser.parse_args();r=execute(args.out,args.wrong_pump_identity,native=args.native,autocad=args.autocad,hk_sources=args.hk_sources,hk_control=args.hk_control)
    print(json.dumps({k:r[k] for k in ('status','stage_errors','verification','design_accepted')},indent=2))
