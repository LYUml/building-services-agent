"""Stage and execute a synthetic IFC selection workflow using an official BEC PDF."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, verify

ROOT = Path(__file__).resolve().parents[1]


def run(pdf, out):
    pdf, out = Path(pdf).resolve(), Path(out).resolve()
    pack = ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json'
    expected = json.loads(pack.read_text())['sources']['emsd_bec_2024']['sha256']
    if digest(pdf) != expected:raise ProjectError('official BEC PDF hash differs from pinned pack')
    if not out.is_relative_to(ROOT) or out == ROOT or out == pdf or out in pdf.parents:
        raise ProjectError('new repository output separate from source required')
    out.mkdir(parents=True, exist_ok=False)
    for name in ('model.json', 'project.json', 'binding.json', 'regulatory-bases.json'):
        shutil.copyfile(ROOT/'examples/circulation-ifc'/name, out/name)
    for name in ('pump-catalogue.json', 'thermal-duty.json'):
        shutil.copyfile(ROOT/'examples/hvac-circulation'/name, out/name)
    shutil.copyfile(ROOT/'examples/ids/pump-selection.ids', out/'pump.ids')
    shutil.copyfile(pack, out/'pack.json'); shutil.copyfile(pdf, out/'emsd-bec-2024.pdf')
    catalogue = json.loads((out/'pump-catalogue.json').read_text())
    catalogue['candidates'] = catalogue['candidates'][-1:]
    catalogue['candidates'][0].update(id='synthetic-revised-curve', head_curve=[[0, 7], [.005, .1]],
                                    source='Explicit synthetic revised curve for workflow demonstration; not a manufacturer product')
    (out/'pump-catalogue.json').write_text(json.dumps(catalogue, indent=2))
    brief = out/'brief.md'
    brief.write_text('Synthetic demonstration: author and bind a circulation IFC; screen a declared pump curve, record the selected curve on a new IFC, recheck thermal and scoped pipe rules, and check pump information. Physical installation and full engineering acceptance remain pending.', encoding='utf-8')
    row = passages(brief)[0]
    tasks = [dict(id='model', kind='bim', project='model.json'),
             dict(id='bound', kind='water_coordination', project='project.json', binding='binding.json', depends_on='model'),
             dict(id='screen', kind='circulation_pump_design', depends_on='bound', catalogue='pump-catalogue.json', thermal_basis='thermal-duty.json', rule_basis='regulatory-bases.json', pack='pack.json', sources='.'),
             dict(id='selected', kind='selected_pump_ifc', depends_on='screen'),
             dict(id='combined', kind='ifc_circulation_checks', depends_on='selected', thermal_basis='thermal-duty.json', rule_basis='regulatory-bases.json', pack='pack.json', sources='.'),
             dict(id='information', kind='ids_check', depends_on='selected', ids='pump.ids'),
             dict(id='water', kind='water_network', depends_on='screen', requires_pass=['combined', 'information'])]
    plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
                passage_dispositions={row['id']: 'requirement'}, tasks=tasks,
                requirements=[dict(id=t['id'], passage=row['id'], quote=row['text'], task=t['id'], acceptance=row['text']) for t in tasks])
    file = out/'plan.json'; file.write_text(json.dumps(plan, indent=2))
    result = execute(file, out/'workflow')
    summary = dict(tasks={k:v['status'] for k,v in result['tasks'].items()},
                   integrity=verify(out/'workflow'), execution_pass=result['execution_pass'], design_accepted=False)
    (out/'summary.json').write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bec-pdf', required=True); parser.add_argument('--out', required=True)
    args = parser.parse_args(); result = run(args.bec_pdf, args.out)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['execution_pass'] and result['integrity']['integrity_pass'] else 2)
