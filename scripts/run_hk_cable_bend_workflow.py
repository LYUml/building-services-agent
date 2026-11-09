"""Same-model official HK cable-table gates with a native calculation schematic."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,verify
from run_hk_cable_bend_demo import run as stage

ROOT=Path(__file__).resolve().parents[1]


def run(out,sources,python,graphviz=None,autocad=None):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository HK cable workflow output required')
    suite=stage(out/'cases',sources)
    shutil.copyfile(ROOT/'regulations/hk/cable-bends-2026.11.10/pack.json',out/'pack.json')
    official=out/'official-sources';official.mkdir()
    shutil.copyfile(Path(sources)/'emsd-wiring-2025.pdf',official/'emsd-wiring-2025.pdf')
    tasks=[];paragraphs=[];requirements=[]
    for case in suite['scenarios']:
        name=case['scenario'];study=name+'-study';rules=name+'-rules';drawing=name+'-drawing';prefix='cases/'+name+'/'
        group=[dict(id=study,kind='three_phase_ifc_project',project=prefix+'source/project.json',ifc=prefix+'selected-model/cables.ifc',binding=prefix+'selected-model/binding.json'),
            dict(id=rules,kind='three_phase_cable_regulations',depends_on=study,ifc=prefix+'selected-model/cables.ifc',binding=prefix+'selected-model/binding.json',basis=prefix+'source/rule-basis.json',pack='pack.json',sources='official-sources'),
            dict(id=drawing,kind='three_phase_drawing',depends_on=study,requires_pass=[rules]),dict(id=name+'-review',kind='manual',requires_pass=[drawing])]
        texts=[name+': derive a fresh electrical study from this exact saved cable model.',
            name+': check selected CoP 2025 25C(1)(h) using native inside radius and explicit source-pinned classifications; unknown/HV scope must not pass.',
            name+': generate a calculation schematic only after this same-model rule check passes.',
            name+': review actual print, manufacturer requirements, no-damage, protection and full Hong Kong installation acceptance separately; synthetic classification is not real product selection.']
        for task,text in zip(group,texts):
            i=len(paragraphs)+1;paragraphs.append(text);tasks.append(task);requirements.append(dict(id='R'+str(i),passage=f'P{i:03}',quote=text,task=task['id'],acceptance=text))
    brief=out/'brief.md';brief.write_text('\n\n'.join(paragraphs),encoding='utf-8')
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={f'P{i:03}':'requirement' for i in range(1,len(paragraphs)+1)},tasks=tasks,requirements=requirements)
    path=out/'plan.json';path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
    result=execute(path,out/'workflow',three_phase_python=python,graphviz=graphviz,autocad=autocad)
    for case in suite['scenarios']:
        name=case['scenario'];expected=case['expected_status'];rows=result['tasks']
        if rows[name+'-study']['status']!='pass' or rows[name+'-rules']['status']!=expected:raise ProjectError('unexpected study/rule workflow result '+name)
        expected_drawing='pass' if expected=='pass' and graphviz and autocad else 'pending'
        if rows[name+'-drawing']['status']!=expected_drawing or expected!='pass' and (out/'workflow'/(name+'-drawing')).exists():raise ProjectError('HK bend gate did not preserve drawing block '+name)
    integrity=verify(out/'workflow')
    if not integrity['integrity_pass']:raise ProjectError('HK cable workflow integrity failed')
    report=dict(tasks=result['tasks'],model_bindings=result['three_phase_model_bindings'],source_bindings=result['three_phase_source_bindings'],integrity=integrity,
        expected_behaviors_pass=True,design_accepted=False,scope='Synthetic saved cable classifications against selected official table; calculation schematic only; full manufacturer/engineering/regulatory review pending')
    (out/'demonstration.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('out','sources','python'):parser.add_argument('--'+key,type=Path,required=True)
    for key in ('graphviz','autocad'):parser.add_argument('--'+key,type=Path)
    r=run(**vars(parser.parse_args()));print(json.dumps({key:r[key] for key in ('expected_behaviors_pass','design_accepted')}))
