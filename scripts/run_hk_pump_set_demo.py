"""Repeatable synthetic duty/standby WSD workflow with pending delivery reviews."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, verify
from bsa.workflow_status import diagnose
from bsa.delivery import template, assess

ROOT = Path(__file__).resolve().parents[1]


def run(pdf, out):
    pdf, out = Path(pdf).resolve(), Path(out).resolve()
    pack_path = ROOT/'regulations/hk/plumbing-pumps-2026.11.09/pack.json'
    pack = json.loads(pack_path.read_text())
    if digest(pdf) != pack['sources']['wsd_tr_2026_04']['sha256']:
        raise ProjectError('official WSD PDF hash differs from pinned pack')
    if not out.is_relative_to(ROOT) or out == ROOT or out == pdf or out in pdf.parents:
        raise ProjectError('new repository output separate from source required')
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT/'examples/hk-plumbing-pumps'
    inputs = {str(p):digest(p) for p in [pdf, pack_path]+[source/n for n in
        ('pump-set.json', 'network.json', 'curve.json', 'binding.json')]}
    summaries = {}
    expected = {'positive': ['pass', 'pass', 'pass'],
                'weak_standby': ['fail', 'pending', 'pending'],
                'missing_duplication': ['pending', 'pending', 'pending']}
    for scenario in expected:
        root = out/scenario; root.mkdir()
        for filename in ('pump-set.json','network.json','curve.json','binding.json'):
            shutil.copyfile(source/filename,root/filename)
        shutil.copyfile(pack_path, root/'pack.json'); shutil.copyfile(pdf, root/'wsd-tr-2026-04.pdf')
        basis = json.loads((root/'binding.json').read_text())
        curve = json.loads((root/'curve.json').read_text())
        if scenario == 'weak_standby':
            for point in curve['points']:point['total_pressure_rise_pa'] *= .1
            curve['sources'][curve['source']] = 'Synthetic weak standby stress case; not a manufacturer product'
        (root/'standby-curve.json').write_text(json.dumps(curve,indent=2))
        pump_set = json.loads((root/'pump-set.json').read_text())
        pump_set['pumps'][1]['curve']='standby-curve.json'
        (root/'pump-set.json').write_text(json.dumps(pump_set,indent=2))
        if scenario == 'missing_duplication':
            del basis['regulatory_basis']['sump_pump']['duplicate_pumpset_provided']
        (root/'binding.json').write_text(json.dumps(basis, indent=2))
        brief = root/'brief.md'
        descriptions=[
            'Synthetic scenario: calculate duty and standby pumps separately against the sourced tank target and scoped WSD pack. Both must satisfy the target alone.',
            'Rerun the duty pump using its checked network and curve only after the entire set passes.',
            'Rerun the standby pump using its checked network and curve only after the entire set passes. Physical equipment, controls, drawings and full regulatory acceptance remain pending.'
        ]
        brief.write_text('\n\n'.join(descriptions),encoding='utf-8')
        rows=passages(brief)
        tasks=[dict(id='capacity',kind='plumbing_pump_set',project='pump-set.json',basis='binding.json',pack='pack.json',sources='.'),
               dict(id='duty',kind='pump_operating_point',project='network.json',curve='curve.json',pump_role='duty',requires_pass=['capacity']),
               dict(id='standby',kind='pump_operating_point',project='network.json',curve='standby-curve.json',pump_role='standby',requires_pass=['capacity'])]
        if len(rows)!=len(tasks):raise ProjectError('brief passage mapping changed; inspect requirements')
        plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),
                  passage_dispositions={row['id']:'requirement' for row in rows},tasks=tasks,
                  requirements=[dict(id=t['id'],passage=row['id'],quote=row['text'],task=t['id'],acceptance=row['text']) for t,row in zip(tasks,rows)])
        file = root/'plan.json'; file.write_text(json.dumps(plan, indent=2))
        result = execute(file, root/'workflow')
        integrity = verify(root/'workflow'); diagnosis = diagnose(file, root/'workflow')
        (root/'diagnosis.json').write_text(json.dumps(diagnosis, indent=2))
        template(file,root/'workflow',root/'delivery-review.json')
        delivery=assess(file,root/'workflow',root/'delivery-review.json')
        (root/'delivery-audit.json').write_text(json.dumps(delivery,indent=2))
        actual = [result['tasks'][t['id']]['status'] for t in tasks]
        role_report=json.loads((root/'workflow/capacity/pump-set-checks.json').read_text())
        role_statuses={r['role']:r['status'] for r in role_report['pump_checks']}
        expected_roles={'duty':'pass','standby':'fail'} if scenario=='weak_standby' else {r:('pass' if scenario=='positive' else 'pending') for r in ('duty','standby')}
        gated = scenario == 'positive' or all(not (root/'workflow'/role).exists() for role in ('duty','standby'))
        summaries[scenario] = dict(task_statuses=dict(zip([t['id'] for t in tasks], actual)),
                                   role_statuses=role_statuses,
                                   expected_behavior_pass=role_statuses==expected_roles and actual == expected[scenario] and gated and integrity['integrity_pass'] and delivery['status']==('failed' if scenario=='weak_standby' else 'needs_review') and not delivery['review_checks_pass'],
                                   integrity=integrity, workflow_execution_pass=result['execution_pass'], delivery=delivery)
    unchanged = all(digest(Path(p)) == sha for p,sha in inputs.items())
    result = dict(inputs=inputs, inputs_unchanged=unchanged, scenarios=summaries,
                  demonstration_checks_pass=unchanged and all(s['expected_behavior_pass'] for s in summaries.values()),
                  design_accepted=False, regulatory_compliance='not_established',
                  scope='Synthetic integration behavior only; expected negative cases remain failed/pending')
    result['artifacts'] = {p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'summary.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wsd-pdf', required=True); parser.add_argument('--out', required=True)
    args = parser.parse_args(); result = run(args.wsd_pdf, args.out)
    print(json.dumps(dict(demonstration_checks_pass=result['demonstration_checks_pass'], design_accepted=False,
                          scenarios={k:dict(tasks=v['task_statuses'],delivery_status=v['delivery']['status']) for k,v in result['scenarios'].items()}),indent=2))
    raise SystemExit(0 if result['demonstration_checks_pass'] else 2)
