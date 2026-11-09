"""Repeatable synthetic IFC/WSD capacity demonstration, including blocked cases."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, verify
from bsa.workflow_status import diagnose

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
        ('route-template.json', 'route-model.json', 'route-binding.json', 'curve.json', 'binding.json')]}
    summaries = {}
    expected = {'positive': ['pass', 'pass', 'pass'],
                'insufficient_capacity': ['pass', 'fail', 'pending'],
                'missing_duplication': ['pass', 'pending', 'pending']}
    for scenario in expected:
        root = out/scenario; root.mkdir()
        for filename, target in (('route-template.json','network.json'), ('route-model.json','model.json'),
                                 ('route-binding.json','binding.json'), ('curve.json','curve.json'), ('binding.json','basis.json')):
            shutil.copyfile(source/filename, root/target)
        shutil.copyfile(pack_path, root/'pack.json'); shutil.copyfile(pdf, root/'wsd-tr-2026-04.pdf')
        basis = json.loads((root/'basis.json').read_text())
        network = json.loads((root/'network.json').read_text())
        if scenario == 'insufficient_capacity':
            network['nodes'][-1]['demand_m3_s'] = .0015
            network['sources']['test'] += '; explicit synthetic 1.5 L/s insufficient-capacity target'
            basis['regulatory_basis']['sump_pump']['tank_design_outflow']['value'] = .0015
        if scenario == 'missing_duplication':
            del basis['regulatory_basis']['sump_pump']['duplicate_pumpset_provided']
        (root/'network.json').write_text(json.dumps(network, indent=2))
        (root/'basis.json').write_text(json.dumps(basis, indent=2))
        brief = root/'brief.md'
        brief.write_text('Synthetic plumbing demonstration: author and bind a saved pipe route; calculate pump capacity against declared tank outflow and scoped WSD requirements; rerun the same pump only after that check passes. Product, tank identity, duplication controls and full engineering acceptance remain pending.', encoding='utf-8')
        row = passages(brief)[0]
        tasks = [dict(id='route', kind='network_coordination', project='network.json', model='model.json', binding='binding.json'),
                 dict(id='capacity', kind='plumbing_pump_regulations', depends_on='route', curve='curve.json', basis='basis.json', pack='pack.json', sources='.'),
                 dict(id='pump', kind='pump_operating_point', depends_on='route', curve='curve.json', requires_pass=['capacity'])]
        plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
                    passage_dispositions={row['id']:'requirement'}, tasks=tasks,
                    requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
        file = root/'plan.json'; file.write_text(json.dumps(plan, indent=2))
        result = execute(file, root/'workflow')
        integrity = verify(root/'workflow'); diagnosis = diagnose(file, root/'workflow')
        (root/'diagnosis.json').write_text(json.dumps(diagnosis, indent=2))
        actual = [result['tasks'][t['id']]['status'] for t in tasks]
        gated = scenario == 'positive' or not (root/'workflow/pump').exists()
        summaries[scenario] = dict(task_statuses=dict(zip([t['id'] for t in tasks], actual)),
                                   expected_behavior_pass=actual == expected[scenario] and gated and integrity['integrity_pass'],
                                   integrity=integrity, workflow_execution_pass=result['execution_pass'])
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
    print(json.dumps({k:result[k] for k in ('scenarios','demonstration_checks_pass','design_accepted')}, indent=2))
    raise SystemExit(0 if result['demonstration_checks_pass'] else 2)
