"""Synthetic saved curved-cable/obstacle coordination release scenarios."""
import argparse
import json
from pathlib import Path
import runpy
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_obstacles import run as append_obstacles
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]


def run(out,python,graphviz=None,autocad=None):
    out,python=Path(out).resolve(),Path(python).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository coordination suite required')
    out.mkdir(parents=True)
    author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
    original=ROOT/'examples/cable-coordination'
    author(original/'project.json',original/'geometry.json',out/'base','mixed-revolution')
    results=[]
    for name,y,expected in [('clear',.10,'pass'),('insufficient-clearance',.025,'fail'),('material-overlap',-.005,'fail')]:
        source=out/name;shutil.copytree(original,source)
        basis=source/'basis.json';data=json.loads(basis.read_text());data['obstacle']['origin_m'][1]=y;basis.write_text(json.dumps(data,indent=2),encoding='utf-8')
        p=json.loads((source/'project.json').read_text())
        for row in p['sources'].values():row['sha256']=digest(basis)
        (source/'project.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
        inventory=json.loads((source/'obstacles.json').read_text());inventory['obstacles'][0]['origin_m'][1]=y;inventory['sources']['assumed']['sha256']=digest(basis)
        (source/'obstacles.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
        policy=json.loads((source/'policy.json').read_text());policy['sources']['assumed']='Synthetic 30 mm clearance target and numerical tolerances in basis.json SHA256 '+digest(basis)+'; no contact waivers or code claim'
        (source/'policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8')
        append_obstacles(out/'base/cables.ifc',source/'obstacles.json',source/'combined')
        binding=json.loads((out/'base/binding.json').read_text());binding['ifc_sha256']=digest(source/'combined/model.ifc')
        (source/'combined/binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
        shutil.copyfile(out/'base/geometry-source.json',source/'combined/geometry-source.json')
        paragraphs=['Derive a fresh electrical study from the saved single circular cable and explicitly sourced combined obstacle model.',
                    'Check all represented physical elements for solid overlap and the declared 30 mm clearance target without contact waivers; retain missing-geometry failures.',
                    'Generate a source-bound calculation schematic and native drawing only after same-model coordination passes.',
                    'Review actual drawings, source obstacle completeness, product fidelity, equipment interfaces, protection and regional requirements separately; this synthetic scope is not full installation acceptance.']
        brief=source/'brief.md';brief.write_text('\n\n'.join(paragraphs),encoding='utf-8')
        ids=['study','coordination','drawing','review']
        plan=dict(version=1,brief=brief.name,brief_sha256=digest(brief),passage_dispositions={f'P{i:03}':'requirement' for i in range(1,5)},tasks=[
            dict(id='study',kind='three_phase_ifc_project',project='project.json',ifc='combined/model.ifc',binding='combined/binding.json'),
            dict(id='coordination',kind='three_phase_coordination',depends_on='study',ifc='combined/model.ifc',binding='combined/binding.json',policy='policy.json'),
            dict(id='drawing',kind='three_phase_drawing',depends_on='study',requires_pass=['coordination']),dict(id='review',kind='manual',requires_pass=['drawing'])],
            requirements=[dict(id=f'R{i}',passage=f'P{i:03}',quote=text,task=task,acceptance=text) for i,(text,task) in enumerate(zip(paragraphs,ids),1)])
        path=source/'plan.json';path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
        r=execute(path,source/'run',three_phase_python=python,graphviz=graphviz,autocad=autocad);integrity=verify(source/'run')
        wanted='pass' if expected=='pass' and graphviz and autocad else 'pending'
        if r['tasks']['study']['status']!='pass' or r['tasks']['coordination']['status']!=expected or r['tasks']['drawing']['status']!=wanted or not integrity['integrity_pass']:raise ProjectError('unexpected cable coordination workflow result')
        if expected!='pass' and (source/'run/drawing').exists():raise ProjectError('failed coordination reached drawing')
        results.append(dict(scenario=name,tasks=r['tasks'],model_bindings=r['three_phase_model_bindings'],inventory_bindings=r['inventory_source_bindings'],integrity=integrity,design_accepted=False))
    result=dict(scope='Synthetic single curved cable/box checks only; no physical joint or complete installation acceptance',scenarios=results,expected_behaviors_pass=True,design_accepted=False)
    (out/'demonstration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('out','python'):p.add_argument('--'+key,type=Path,required=True)
    for key in ('graphviz','autocad'):p.add_argument('--'+key,type=Path)
    a=p.parse_args();r=run(a.out,a.python,a.graphviz,a.autocad)
    print(json.dumps({k:r[k] for k in ('expected_behaviors_pass','design_accepted')}))
