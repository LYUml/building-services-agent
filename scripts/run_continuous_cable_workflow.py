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


def run(out, python, graphviz=None, autocad=None, inside_limit=.28, route=False, include_obstacles=False,lead=0.,quarter_turn=False,hk_sources=None,hk_unknown_construction=False):
    if hk_unknown_construction and not hk_sources:raise ProjectError('HK classification control requires selected HK sources')
    if include_obstacles and not route:raise ProjectError('obstacle projection requires route mode')
    if not math.isfinite(inside_limit) or inside_limit <= 0:
        raise ProjectError('positive finite synthetic inside-radius target required')
    out = Path(out).resolve()
    stage(out, python,lead=lead,rotation_deg=90. if quarter_turn else 0.)
    source = out / 'source'
    append_obstacles(out / 'fixture/cables.ifc', source / 'obstacles.json', out / 'combined')
    binding = json.loads((out / 'fixture/binding.json').read_text())
    shutil.copyfile(out / 'fixture/geometry-source.json', out / 'combined/geometry-source.json')
    shutil.copyfile(ROOT / 'examples/cable-bend-limits/basis.txt', source / 'limit-basis.txt')
    text = (source / 'limit-basis.txt').read_text().replace('0.280 m', f'{inside_limit:.9f} m')
    classification=dict(source='synthetic',product_reference='synthetic-cable-20',overall_diameter_mm=20.,overall_diameter_is_actual=True,
        wiring_scope_confirmed=True,low_voltage=True,pvc_insulated=None if hk_unknown_construction else True,stranded_copper=True,armoured=False)
    if hk_sources:text+='\nExplicit synthetic CoP 2025 edition/classification assumptions only; no actual manufacturer or statutory authentication:\n'+json.dumps(classification,indent=2)
    (source / 'limit-basis.txt').write_text(text, encoding='utf-8')
    limits = json.loads((ROOT / 'examples/cable-bend-limits/limits.json').read_text())
    limits['bends']['feeder']['minimum_radius_m'] = inside_limit
    limits['sources']['synthetic'].update(path='limit-basis.txt', sha256=digest(source / 'limit-basis.txt'))
    (source / 'limits.json').write_text(json.dumps(limits, indent=2), encoding='utf-8')
    if hk_sources:
        shutil.copyfile(ROOT/'regulations/hk/cable-bends-2026.11.10/pack.json',out/'hk-pack.json')
        official=out/'hk-sources';official.mkdir();shutil.copyfile(Path(hk_sources)/'emsd-wiring-2025.pdf',official/'emsd-wiring-2025.pdf')
        hk_basis=dict(version=1,sources={'synthetic':limits['sources']['synthetic']},jurisdiction='HK',rule_pack='hk-cable-bends-2026.11.10',
            edition_decision=dict(edition='2025',source='synthetic'),bends={'feeder':classification})
        (source/'hk-basis.json').write_text(json.dumps(hk_basis,indent=2),encoding='utf-8')
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
        'Derive and solve a fresh electrical project from the saved single-quarter continuous cable and sourced obstacle IFC.',
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
    if route:
        drawing_settings=dict(projection_axes=['X','Z'],annotation_height_m=.04,source='Synthetic X/Z route projection and 40 mm model text; no installation acceptance')
        native_settings=dict(source='Synthetic A4 1:20 route view; 2 m saved tail straight reference; declared lead included in window',window_drawing_units=[-2.3,1.1,2.7,2.9+lead],scale_denominator=20,
            reference_ifc_guid=cable.GlobalId,reference_layer='BSA_CABLE_AXIS',drawing_name='cable-route',pdf_tolerance_mm=.2)
        if quarter_turn:native_settings.update(source='Independent synthetic 90-degree rotated case; explicit A4 1:25 window and 2 m tail reference; no automatic fit',window_drawing_units=[-1.5,1.,4.2,5.],scale_denominator=25)
        (out/'route-settings.json').write_text(json.dumps(drawing_settings,indent=2),encoding='utf-8')
        (out/'route-native-settings.json').write_text(json.dumps(native_settings,indent=2),encoding='utf-8')
        tasks[3].update(kind='cable_route_drawing',ifc='combined/model.ifc',binding='combined/binding.json',settings='route-settings.json',native_settings='route-native-settings.json')
        if include_obstacles:tasks[3]['obstacles']='source/obstacles.json'
        paragraphs[3]='Generate the selected cable true-arc/OD route view only after same-model study, bend and coordination checks pass; explicitly omit other elements and separately inspect the reopened native DWG/PDF.'
        if include_obstacles:paragraphs[3]='Generate the cable true-arc/OD route view and all source-checked box projections only after same-model study, bend and coordination checks pass; show depth intervals and separately inspect native DWG/PDF; projection alone does not prove clearance.'
        brief.write_text('\n\n'.join(paragraphs),encoding='utf-8')
    if hk_sources:
        tasks[3]['requires_pass'].append('hk-bend')
        tasks.insert(3,dict(id='hk-bend',kind='three_phase_cable_regulations',depends_on='study',ifc='combined/model.ifc',binding='combined/binding.json',basis='source/hk-basis.json',pack='hk-pack.json',sources='hk-sources'))
        paragraphs.insert(3,'Check selected HK CoP 2025 cable inside-radius table against this same model and explicit synthetic classifications; this must not override failed declared product limits or coordination checks.')
        brief.write_text('\n\n'.join(paragraphs),encoding='utf-8')
    plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
        passage_dispositions={f'P{i:03}': 'requirement' for i in range(1, len(paragraphs)+1)}, tasks=tasks,
        requirements=[dict(id=f'R{i}', passage=f'P{i:03}', quote=text, task=task['id'], acceptance=text)
            for i, (text, task) in enumerate(zip(paragraphs, tasks), 1)])
    path = out / 'plan.json'
    path.write_text(json.dumps(plan, indent=2), encoding='utf-8')
    result = execute(path, out / 'workflow', three_phase_python=python, graphviz=graphviz, autocad=autocad)
    integrity = verify(out / 'workflow')
    statuses = {name: row['status'] for name, row in result['tasks'].items()}
    bend_status = 'pass' if .29 >= inside_limit else 'fail'
    hk_status='pending' if hk_unknown_construction else 'pass'
    expected = dict(study='pass', bend=bend_status, coordination='pass', drawing='pass' if (route or graphviz) and autocad and bend_status=='pass' and (not hk_sources or hk_status=='pass') else 'pending', review='pending')
    if hk_sources:expected['hk-bend']=hk_status
    if statuses != expected or not integrity['integrity_pass']:
        raise ProjectError('continuous cable workflow did not reach expected scoped result: ' + str(statuses))
    if (bend_status != 'pass' or hk_sources and hk_status!='pass') and (out / 'workflow/drawing').exists():
        raise ProjectError('failed bend check reached drawing adapter')
    report = dict(tasks=statuses, integrity=integrity, model_bindings=result['three_phase_model_bindings'],
                  scope=('Synthetic cable and source-box route projection; depth and visual/engineering review separate' if include_obstacles else 'Synthetic selected cable route; obstacle omitted from drawing; visual and engineering review pending' if route else 'Synthetic continuous cable and box; schematic only; visual and engineering review pending'), design_accepted=False)
    (out / 'workflow-summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('out', 'python'):
        parser.add_argument('--' + key, type=Path, required=True)
    for key in ('graphviz', 'autocad'):
        parser.add_argument('--' + key, type=Path)
    parser.add_argument('--inside-limit', type=float, default=.28)
    parser.add_argument('--route', action='store_true')
    parser.add_argument('--include-obstacles',action='store_true')
    parser.add_argument('--lead',type=float,default=0.)
    parser.add_argument('--quarter-turn',action='store_true')
    parser.add_argument('--hk-sources',type=Path)
    parser.add_argument('--hk-unknown-construction',action='store_true')
    print(json.dumps(run(**vars(parser.parse_args()))['tasks']))
