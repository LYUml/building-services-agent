"""Repeatable synthetic declared-connection/stack-demand workflow, not design acceptance."""
import argparse
import json
import math
from pathlib import Path
import shutil

from bsa.cli import digest
from bsa.drainage_connections import OFFICIAL_SHA256
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, verify
from bsa.workflow_status import diagnose

ROOT = Path(__file__).resolve().parents[1]


def run(pdf, out):
    pdf, out = Path(pdf).resolve(), Path(out).resolve()
    if digest(pdf) != OFFICIAL_SHA256:
        raise ProjectError('Official APP-164 November 2023 bytes do not match the pinned source')
    if not out.is_relative_to(ROOT) or out == ROOT or out == pdf or out in pdf.parents:
        raise ProjectError('New repository-local output outside source required')
    pins = {str(p): digest(p) for p in (pdf, Path(__file__).resolve())}
    out.mkdir(parents=True, exist_ok=False)
    summary = {}
    expected = {'positive': ['pass', 'pass', 'pending'],
                'upper_route_unknown': ['pass', 'pending', 'pending'],
                'prohibited_connection': ['fail', 'pending', 'pending']}
    for case in expected:
        root = out/case; root.mkdir()
        shutil.copyfile(pdf, root/'APP164.pdf')
        note = root/'synthetic-survey-and-du.txt'
        note.write_text('Fictional software demonstration only. Building has 24 storeys; stack discharges at offset 0. '
                        'Individual fixtures A/B on offsets 0/1 use separate manhole pipes, C/D on offsets 2/3 use the stack. '
                        'Synthetic DU values A=8 B=4 C=2 D=3; K=0.5. These are assumed test values, not fixture table entries, '
                        'a real survey or a legal applicability determination.', encoding='utf-8')
        fixtures = [dict(id=name, floor_offset=floor, connected_to_stack=main,
                         separate_to_manhole=not main, source=note.name)
                    for name, floor, main in [('A', 0, False), ('B', 1, False), ('C', 2, True), ('D', 3, True)]]
        if case == 'upper_route_unknown': fixtures[2]['connected_to_stack'] = None
        if case == 'prohibited_connection': fixtures[1]['connected_to_stack'] = True
        project = dict(scope=dict(building_storeys=24, stack_scope='building',
                        edition_basis='November 2023 selected for synthetic method exercise only',
                        works_basis='Synthetic exercise assumes reviewed 2(d)/(e) applicability; not an actual works decision',
                        evidence=note.name), fixtures=fixtures, inventory_complete=True, inventory_source=note.name,
                       references={'APP164.pdf': OFFICIAL_SHA256, note.name: digest(note)}, official_reference='APP164.pdf')
        basis = dict(fixture_units={name: dict(value=value, source=note.name, classification='assumed')
                                    for name, value in [('A', 8), ('B', 4), ('C', 2), ('D', 3)]},
                     frequency_factor=dict(value=.5, source=note.name, classification='assumed'),
                     full_stack_inventory_verified=True, frequency_classification_verified=True,
                     basis='Synthetic entire four-fixture inventory for integration verification only',
                     references={note.name: digest(note)})
        for filename, data in [('connections.json', project), ('basis.json', basis)]:
            (root/filename).write_text(json.dumps(data, indent=2), encoding='utf-8')
        brief = root/'brief.txt'
        brief.write_text('Synthetic exercise: review declared restricted-floor connections and derive same-inventory stack demand; retain complete engineering review.\n', encoding='utf-8')
        passage = passages(brief)[0]
        tasks = [dict(id='connections', kind='drainage_connections', project='connections.json'),
                 dict(id='demand', kind='drainage_stack_demand', depends_on='connections', basis='basis.json'),
                 dict(id='engineering', kind='manual', requires_pass=['demand'],
                      description='Real survey, other inflows, sizing/venting, geometry and complete acceptance pending')]
        plan = dict(version=1, brief=brief.name, brief_sha256=digest(brief),
                    passage_dispositions={passage['id']: 'requirement'}, tasks=tasks,
                    requirements=[dict(id=t['id'], passage=passage['id'], quote=passage['text'],
                                       task=t['id'], acceptance=passage['text']) for t in tasks])
        plan_path = root/'plan.json'; plan_path.write_text(json.dumps(plan, indent=2), encoding='utf-8')
        result = execute(plan_path, root/'workflow')
        integrity = verify(root/'workflow')
        (root/'diagnosis.json').write_text(json.dumps(diagnose(plan_path, root/'workflow'), indent=2), encoding='utf-8')
        actual = [result['tasks'][t['id']]['status'] for t in tasks]
        demand_path = root/'workflow/demand/stack-demand.json'
        numerical = False
        if case == 'positive':
            demand = json.loads(demand_path.read_text(encoding='utf-8'))
            numerical = (demand['included_fixture_ids'] == ['C', 'D']
                         and demand['excluded_direct_manhole_fixture_ids'] == ['A', 'B']
                         and demand['calculation']['total_DU'] == 5
                         and math.isclose(demand['calculation']['wastewater_flow_L_s'], .5*math.sqrt(5), rel_tol=1e-12))
        elif case == 'upper_route_unknown':
            numerical = json.loads(demand_path.read_text(encoding='utf-8'))['calculation'] is None
        else:
            numerical = not (root/'workflow/demand').exists()
        summary[case] = dict(task_statuses=dict(zip([t['id'] for t in tasks], actual)),
                             expected_behavior_pass=actual == expected[case] and numerical and integrity['integrity_pass'],
                             integrity_pass=integrity['integrity_pass'], design_accepted=result['design_accepted'])
    unchanged = all(digest(Path(p)) == sha for p, sha in pins.items())
    result = dict(inputs=pins, inputs_unchanged=unchanged, scenarios=summary,
                  demonstration_checks_pass=unchanged and all(s['expected_behavior_pass'] and not s['design_accepted'] for s in summary.values()),
                  design_accepted=False, regulatory_compliance='not_established',
                  scope='Synthetic software integration evidence only; negative/pending cases and engineering review remain unresolved')
    result['artifacts'] = {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app164-pdf', required=True); parser.add_argument('--out', required=True)
    args = parser.parse_args(); result = run(args.app164_pdf, args.out)
    print(json.dumps({k: result[k] for k in ('scenarios', 'demonstration_checks_pass', 'design_accepted')}, indent=2))
    raise SystemExit(0 if result['demonstration_checks_pass'] else 2)
