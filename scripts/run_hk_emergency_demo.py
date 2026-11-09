"""Exercise assertion-only emergency rules and workflow gates with official evidence."""
import argparse
import copy
import json
from pathlib import Path
import shutil

from bsa.cli import digest
from bsa.regulation_coverage import run as coverage
from bsa.workflow import execute, passages, verify


ROOT = Path(__file__).resolve().parents[1]


def run(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    if not out.is_relative_to(ROOT) or out == ROOT or out.exists():
        raise ValueError('new repository-local output directory required')
    pack_path = ROOT / 'regulations/hk/emergency-accommodation-2026.11.09/pack.json'
    pack = json.loads(pack_path.read_text())
    official = pack['sources']['fsd_guidance_2021']
    if digest(source) != official['sha256']:
        raise ValueError('pinned FSD guidance PDF required')
    base = json.loads((ROOT / 'examples/regulations-hk/emergency-accommodation.json').read_text())
    out.mkdir(parents=True)
    shutil.copyfile(source, out / official['cache_filename'])
    shutil.copyfile(pack_path, out / 'pack.json')
    scope = ROOT / 'examples/regulations-hk/coverage-scope-emergency.json'
    catalog = ROOT / 'regulations/hk/coverage-2026.11.09-emergency.json'
    results = []
    for name, expected in [('asserted-pass', 'pass'), ('low-illuminance', 'pending'), ('normal-mode', 'pending')]:
        folder = out / name
        folder.mkdir()
        project = copy.deepcopy(base)
        if name == 'low-illuminance':
            project['emergency_accommodation']['minimum_illuminance']['value'] = 1.9
        if name == 'normal-mode':
            project['emergency_accommodation']['emergency_mode']['value'] = False
        (folder / 'project.json').write_text(json.dumps(project))
        # Workflow paths stay within each plan directory.
        shutil.copyfile(out / 'pack.json', folder / 'pack.json')
        shutil.copyfile(out / official['cache_filename'], folder / official['cache_filename'])
        brief = folder / 'brief.md'
        brief.write_text('Check synthetic emergency accommodation assertions before manual delivery review.')
        p = passages(brief)[0]
        plan = dict(version=1, brief='brief.md', brief_sha256=digest(brief),
            passage_dispositions={p['id']: 'requirement'},
            tasks=[dict(id='emergency', kind='regulations', project='project.json', pack='pack.json', sources='.'),
                   dict(id='delivery', kind='manual', requires_pass=['emergency'], description='Physical, photometric and engineering review still required')],
            requirements=[dict(id='R1', passage=p['id'], quote=p['text'], task='emergency', acceptance='Compare sourced assertions only'),
                          dict(id='R2', passage=p['id'], quote=p['text'], task='delivery', acceptance='Independent engineering delivery review')])
        plan_path = folder / 'plan.json'
        plan_path.write_text(json.dumps(plan))
        planning = coverage(catalog, scope, folder / 'coverage', plan_path)
        topic = next(t for t in planning['topics'] if t['id'] == 'emergency_lighting')
        assert topic['modules'][0]['scheduled_tasks'] == ['emergency']
        assert topic['gaps'] == ['partial_rule_coverage']
        result = execute(plan_path, folder / 'run')
        integrity = verify(folder / 'run')
        assert integrity['integrity_pass'], integrity
        assert result['tasks']['emergency']['status'] == expected, result['tasks']
        assert result['tasks']['delivery']['status'] == 'pending'
        if expected != 'pass':
            assert 'adapter not executed' in result['tasks']['delivery']['scope']
            assert not (folder / 'run' / 'delivery').exists()
        results.append(dict(scenario=name, tasks=result['tasks'], integrity=integrity,
                            planning_gaps=topic['gaps'], design_accepted=False))
    report = dict(scope='Synthetic sourced assertions; no emergency simulation or engineering acceptance',
                  official_source_sha256=official['sha256'], scenarios=results)
    (out / 'demonstration.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.out), indent=2))
