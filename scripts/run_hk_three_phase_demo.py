"""Synthetic three-phase numerical/rule/native workflow with retained blockers."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.workflow_status import diagnose
from bsa.regulation_coverage import run as coverage

ROOT=Path(__file__).resolve().parents[1]


def run(source,out,python,graphviz=None,autocad=None):
    source,out,python=[Path(v).resolve() for v in (source,out,python)]
    if not out.is_relative_to(ROOT) or out==ROOT or out.exists():raise ValueError('new repository-local output required')
    pack_path=ROOT/'regulations/hk/phase-balance-2026.11.10/pack.json'
    pack=json.loads(pack_path.read_text());official=pack['sources']['emsd_bec_2024']
    if digest(source)!=official['sha256']:raise ValueError('pinned official BEC PDF required')
    out.mkdir(parents=True)
    summary=[]
    for name,expected in [('conditional-pass','pass'),('unbalanced-in-scope','pending'),('missing-design-basis','pending')]:
        folder=out/name
        shutil.copytree(ROOT/'examples/three-phase-network',folder)
        shutil.copyfile(pack_path,folder/'pack.json');shutil.copyfile(source,folder/official['cache_filename'])
        basis=json.loads((folder/'hk-basis.json').read_text(encoding='utf-8-sig'))
        document=folder/'hk-basis.md';text=document.read_text(encoding='utf-8')
        if name=='unbalanced-in-scope':
            basis['circuits']['branch']['protective_device_rating']['value']=400
            text=text.replace('branch protective-device rating is 63 A','branch protective-device rating is 400 A')
        if name=='missing-design-basis':
            for circuit in basis['circuits'].values():
                del circuit['facts']['design_normal_service_rms_confirmed']
                del circuit['facts']['sinusoidal_design_model_applicable']
            text=text.replace('Assume the modelled constant-PQ operating point is the normal-service RMS design condition and the sinusoidal fundamental model is applicable to that condition.',
                'Normal-service RMS design condition and sinusoidal model applicability are unresolved in this negative software scenario.')
        document.write_text(text,encoding='utf-8');basis['sources']['scenario']['sha256']=digest(document)
        (folder/'hk-basis.json').write_text(json.dumps(basis,indent=2),encoding='utf-8')
        paragraphs=[
            'Execute the declared synthetic three-phase numerical study with independent verification and explicit study targets.',
            'Check the selected BEC 2024 current-balance clause using the same study and explicitly sourced conditional circuit/rating/RMS basis; preserve missing or exceeded checks.',
            'Generate the source-bound calculation schematic, phase schedules, native DWG and measured PDF only after numerical and selected-rule prerequisites pass.',
            'Review the actual PDF and full installation/protection/neutral/harmonic/Hong Kong scope separately; preserve incomplete engineering acceptance.']
        brief=folder/'regulated-brief.md';brief.write_text('\n\n'.join(paragraphs),encoding='utf-8')
        task_ids=['power-flow','hk-rule','drawing','review']
        plan=dict(version=1,brief=brief.name,brief_sha256=digest(brief),passage_dispositions={f'P{i:03}':'requirement' for i in range(1,5)},tasks=[
            dict(id='power-flow',kind='three_phase',project='project.json'),
            dict(id='hk-rule',kind='three_phase_regulations',depends_on='power-flow',basis='hk-basis.json',pack='pack.json',sources='.'),
            dict(id='drawing',kind='three_phase_drawing',depends_on='power-flow',requires_pass=['hk-rule']),
            dict(id='review',kind='manual',requires_pass=['drawing'],description='Actual visual and full engineering acceptance remain separate')],
            requirements=[dict(id='R'+str(i),passage=f'P{i:03}',quote=text,task=task,
                acceptance=text+' Scope is the declared synthetic scenario, not an actual accepted design.') for i,(task,text) in enumerate(zip(task_ids,paragraphs),1)])
        path=folder/'regulated-plan.json';path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
        planning=coverage(ROOT/'regulations/hk/coverage-2026.11.10-phase-balance.json',ROOT/'examples/regulations-hk/coverage-scope-phase-balance.json',folder/'coverage',path)
        topic=next(t for t in planning['topics'] if t['id']=='electrical_current_balance')
        assert topic['modules'][0]['scheduled_tasks']==['hk-rule']
        assert topic['gaps']==['partial_rule_coverage']
        result=execute(path,folder/'run',three_phase_python=python,graphviz=graphviz,autocad=autocad)
        check=verify(folder/'run');diagnosis=diagnose(path,folder/'run')
        assert check['integrity_pass'],check
        assert result['tasks']['power-flow']['status']=='pass',result['tasks']
        assert result['tasks']['hk-rule']['status']==expected,result['tasks']
        wanted='pass' if expected=='pass' and graphviz and autocad else 'pending'
        assert result['tasks']['drawing']['status']==wanted,result['tasks']
        assert result['tasks']['review']['status']=='pending'
        if expected!='pass':assert not (folder/'run/drawing').exists()
        assert result['three_phase_source_bindings']==[dict(check='hk-rule',consumer='drawing',study_producer='power-flow')]
        summary.append(dict(scenario=name,tasks=result['tasks'],integrity=check,
            source_bindings=result['three_phase_source_bindings'],diagnosis=diagnosis,selected_topic_gaps=topic['gaps'],design_accepted=False))
    result=dict(scope='Synthetic selected-clause workflow only; no complete installation or regulatory acceptance',
        official_sha256=official['sha256'],scenarios=summary,expected_behaviors_pass=True,design_accepted=False)
    (out/'demonstration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','out','python'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('graphviz','autocad'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();r=run(a.source,a.out,a.python,a.graphviz,a.autocad)
    print(json.dumps(dict(expected_behaviors_pass=r['expected_behaviors_pass'],design_accepted=False)))
