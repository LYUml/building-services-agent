"""Source-linked synthetic native bend-limit workflow with blocking controls."""
import argparse
import json
from pathlib import Path
import runpy
import shutil
import ifcopenshell
import ifcopenshell.api as api
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]


def run(out,python,graphviz=None,autocad=None):
    out,python=Path(out).resolve(),Path(python).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository suite output required')
    out.mkdir(parents=True)
    author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
    author(ROOT/'examples/three-phase-bend/project.json',ROOT/'examples/three-phase-bend/geometry.json',out/'base-model','mixed-revolution')
    cases=[]
    for name,expected in [('conditional-pass','pass'),('inside-radius-too-small','fail'),('unknown-radius-reference','pending')]:
        source=out/name;shutil.copytree(ROOT/'examples/three-phase-bend',source)
        shutil.copytree(out/'base-model',source/'cable-fixture')
        shutil.copyfile(ROOT/'examples/cable-bend-limits/basis.txt',source/'limit-basis.txt')
        limit=json.loads((ROOT/'examples/cable-bend-limits/limits.json').read_text())
        text=(source/'limit-basis.txt').read_text()
        if name=='inside-radius-too-small':
            limit['bends']['feeder']['minimum_radius_m']=.295
            text=text.replace('0.280 m','0.295 m')
        if name=='unknown-radius-reference':
            limit['bends']['feeder']['radius_reference']='unknown'
            text=text.replace('minimum inside radius','minimum radius with unresolved measurement reference')
        (source/'limit-basis.txt').write_text(text,encoding='utf-8')
        limit['sources']['synthetic'].update(path='limit-basis.txt',sha256=digest(source/'limit-basis.txt'),locator='Synthetic diameter, installation condition and bend-radius requirement paragraph')
        (source/'limits.json').write_text(json.dumps(limit,indent=2),encoding='utf-8')
        native=source/'cable-fixture';binding=json.loads((native/'binding.json').read_text())
        model=ifcopenshell.open(str(native/'cables.ifc'));obj=model.by_guid(binding['lines']['feeder']['element_guid'])
        ps=api.run('pset.add_pset',model,product=obj,name='BSA_CableSelection')
        api.run('pset.edit_pset',model,pset=ps,properties=dict(ProductReference='synthetic-cable-20',SourceSHA256=limit['sources']['synthetic']['sha256'],InstallationCondition='installed'))
        model.write(str(native/'cables.ifc'));binding['ifc_sha256']=digest(native/'cables.ifc')
        (native/'binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
        paragraphs=['Derive a new source-bound electrical project from saved straight/quarter-circle cable geometry and execute a fresh numerical study.',
                    'Check the declared synthetic product diameter, native product/source/installation condition and explicitly stated bend-radius requirement; unresolved information must not pass.',
                    'Generate a calculation schematic and native outputs only after that same-model bend requirement passes.',
                    'Review the actual PDF and full product selection, physical routing, protection and Hong Kong regulatory scope separately; synthetic targets are not accepted hardware.']
        brief=source/'limit-brief.md';brief.write_text('\n\n'.join(paragraphs),encoding='utf-8')
        ids=['study','bend-check','drawing','review']
        plan=dict(version=1,brief=brief.name,brief_sha256=digest(brief),passage_dispositions={f'P{i:03}':'requirement' for i in range(1,5)},tasks=[
            dict(id='study',kind='three_phase_ifc_project',project='project.json',ifc='cable-fixture/cables.ifc',binding='cable-fixture/binding.json'),
            dict(id='bend-check',kind='three_phase_bend_limits',depends_on='study',ifc='cable-fixture/cables.ifc',binding='cable-fixture/binding.json',basis='limits.json'),
            dict(id='drawing',kind='three_phase_drawing',depends_on='study',requires_pass=['bend-check']),dict(id='review',kind='manual',requires_pass=['drawing'])],
            requirements=[dict(id=f'R{i}',passage=f'P{i:03}',quote=text,task=task,acceptance=text) for i,(text,task) in enumerate(zip(paragraphs,ids),1)])
        path=source/'plan.json';path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
        result=execute(path,source/'run',three_phase_python=python,graphviz=graphviz,autocad=autocad)
        integrity=verify(source/'run')
        if result['tasks']['study']['status']!='pass' or result['tasks']['bend-check']['status']!=expected or not integrity['integrity_pass']:raise ProjectError('unexpected bend workflow outcome')
        expected_drawing='pass' if expected=='pass' and graphviz and autocad else 'pending'
        if result['tasks']['drawing']['status']!=expected_drawing or (expected!='pass' and (source/'run/drawing').exists()):raise ProjectError('bend release gate did not preserve expected blocking')
        cases.append(dict(scenario=name,tasks=result['tasks'],model_bindings=result['three_phase_model_bindings'],integrity=integrity,design_accepted=False))
    report=dict(scope='Synthetic declared-limit workflow only; not manufacturer/cable/Hong Kong acceptance',scenarios=cases,expected_behaviors_pass=True,design_accepted=False)
    (out/'demonstration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('out','python'):p.add_argument('--'+key,type=Path,required=True)
    for key in ('graphviz','autocad'):p.add_argument('--'+key,type=Path)
    a=p.parse_args();r=run(a.out,a.python,a.graphviz,a.autocad)
    print(json.dumps({k:r[k] for k in ('expected_behaviors_pass','design_accepted')}))
