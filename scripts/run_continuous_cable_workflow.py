"""Same-model synthetic continuous cable study/bend/coordination/drawing trial."""
import argparse
import json
import math
from pathlib import Path
import shutil
import ifcopenshell
import ifcopenshell.api as api
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_obstacles import run as append_obstacles
from bsa.workflow import execute, verify
from run_continuous_cable_demo import run as stage

ROOT = Path(__file__).resolve().parents[1]


def run(out, python, graphviz=None, autocad=None, inside_limit=.28):
    if not math.isfinite(inside_limit) or inside_limit <= 0:
        raise ProjectError('positive finite synthetic inside-radius target required')
    out = Path(out).resolve()
    stage(out, python)
    source = out / 'source'
    append_obstacles(out / 'fixture/cables.ifc', source / 'obstacles.json', out / 'combined')
    binding = json.loads((out / 'fixture/binding.json').read_text())
    shutil.copyfile(out / 'fixture/geometry-source.json', out / 'combined/geometry-source.json')
    shutil.copyfile(ROOT / 'examples/cable-bend-limits/basis.txt', source / 'limit-basis.txt')
    text = (source / 'limit-basis.txt').read_text().replace('0.280 m', f'{inside_limit:.9f} m')
    (source / 'limit-basis.txt').write_text(text, encoding='utf-8')
    limits = json.loads((ROOT / 'examples/cable-bend-limits/limits.json').read_text())
    limits['bends']['feeder']['minimum_radius_m'] = inside_limit
    limits['sources']['synthetic'].update(path='limit-basis.txt', sha256=digest(source / 'limit-basis.txt'))
    (source / 'limits.json').write_text(json.dumps(limits, indent=2), encoding='utf-8')
    model_path = out / 'combined/model.ifc'
    model = ifcopenshell.open(str(model_path))
    cable = model.by_guid(binding['lines']['feeder']['element_guid'])
    pset = api.run('pset.add_pset', model, product=cable, name='BSA_CableSelection')
    api.run('pset.edit_pset', model, pset=pset, properties=dict(ProductReference='synthetic-cable-20',
        SourceSHA256=limits['sources']['synthetic']['sha256'], InstallationCondition='installed'))
    model.write(str(model_path))
    binding['ifc_sha256'] = digest(model_path)
    (out / 'combined/binding.json').write_text(json.dumps(binding, indent=2), encoding='utf-8')
    paragraphs = [
        'Derive and solve a fresh electrical project from the saved continuous quarter-plus-tangent cable and sourced obstacle IFC.',
        'Check its single bend against explicitly assumed diameter, installation condition and inside-radius limit; this is not manufacturer selection.',
        'Check all represented model solids for material overlap and the assumed 30 mm clearance; physical joint and obstacle completeness remain unverified.',
        'Generate a calculation schematic only after same-model bend and coordination checks pass; reopen native DWG and separately inspect the PDF.',
        'Keep full installation, protection, product, Hong Kong regulations and engineering acceptance pending.']
    brief = out / 'brief.md'
    brief.write_text('\n\n'.join(paragraphs), encoding='utf-8')
    tasks = [dict(id='study', kind='three_phase_ifc_project', project='source/project.json', ifc='combined/model.ifc', binding='combined/binding.json'),
        dict(id='bend', kind='three_phase_bend_limits', depends_on='study', ifc='combined/model.ifc', binding='combined/binding.json', basis='source/limits.json'),
        dict(id='coordination', kind='three_phase_coordination', depends_on='study', ifc='combined/model.ifc', binding='combined/binding.json', policy='source/policy.json'),
        dict(id='drawing', kind='three_phase_drawing', depends_on='study', requires_pass=['bend', 'coordination']),
        dict(id='review', kind='manual', requires_pass=['drawing'])]
    plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
        passage_dispositions={f'P{i:03}': 'requirement' for i in range(1, 6)}, tasks=tasks,
        requirements=[dict(id=f'R{i}', passage=f'P{i:03}', quote=text, task=task['id'], acceptance=text)
            for i, (text, task) in enumerate(zip(paragraphs, tasks), 1)])
    path = out / 'plan.json'
    path.write_text(json.dumps(plan, indent=2), encoding='utf-8')
    result = execute(path, out / 'workflow', three_phase_python=python, graphviz=graphviz, autocad=autocad)
    integrity = verify(out / 'workflow')
    statuses = {name: row['status'] for name, row in result['tasks'].items()}
    bend_status = 'pass' if .29 >= inside_limit else 'fail'
    expected = dict(study='pass', bend=bend_status, coordination='pass', drawing='pass' if graphviz and autocad and bend_status=='pass' else 'pending', review='pending')
    if statuses != expected or not integrity['integrity_pass']:
        raise ProjectError('continuous cable workflow did not reach expected scoped result: ' + str(statuses))
    if bend_status != 'pass' and (out / 'workflow/drawing').exists():
        raise ProjectError('failed bend check reached drawing adapter')
    report = dict(tasks=statuses, integrity=integrity, model_bindings=result['three_phase_model_bindings'],
                  scope='Synthetic continuous cable and box; schematic only; visual and engineering review pending', design_accepted=False)
    (out / 'workflow-summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('out', 'python'):
        parser.add_argument('--' + key, type=Path, required=True)
    for key in ('graphviz', 'autocad'):
        parser.add_argument('--' + key, type=Path)
    parser.add_argument('--inside-limit', type=float, default=.28)
    print(json.dumps(run(**vars(parser.parse_args()))['tasks']))
