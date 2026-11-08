"""Stage synthetic native-energy/regulatory workflow with a pinned official PDF."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,passages
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


def stage(out,official,negative=False):
    out=Path(out).resolve();official=Path(official).resolve()
    pack=ROOT/'regulations/hk/hvac-design-2026.11.08/pack.json'
    metadata=json.loads(pack.read_text())['sources']['emsd_bec_2024']
    if not official.is_file() or digest(official)!=metadata['sha256']:raise ProjectError('pinned official BEC PDF required')
    project=ROOT/('examples/sizing-humidity/project.json' if negative else 'examples/regulations-hk-hvac/native-energy-project.json')
    inputs={project:'project.json',pack:'pack.json',ROOT/'examples/regulations-hk-hvac/zone-bases.json':'basis.json',official:metadata['cache_filename']}
    if out==ROOT or not out.is_relative_to(ROOT) or any(out==p or out in p.parents for p in inputs):raise ProjectError('new staging folder must be inside repository and separate from sources')
    before={str(p):digest(p) for p in inputs};out.mkdir(parents=True,exist_ok=False)
    for src,name in inputs.items():
        shutil.copy2(src,out/name)
        if digest(out/name)!=before[str(src)]:raise ProjectError('staged copy differs')
    brief=out/'brief.md'
    brief.write_text('Run both synthetic design-day lighting variants with actual EnergyPlus.\n\nCheck both executed native models against the selected Hong Kong design-condition pack.\n\nReview remaining HVAC clauses and actual project applicability after supported checks pass.',encoding='utf-8')
    tasks=[dict(id='energy',kind='energy',project='project.json'),
           dict(id='hk',kind='hvac_regulations',depends_on='energy',basis='basis.json',pack='pack.json',sources='.'),
           dict(id='review',kind='manual',requires_pass=['hk'],description='Remaining HVAC clauses, maintained states and actual project acceptance need review')]
    rows=passages(brief)
    if len(rows)!=len(tasks):raise ProjectError('brief coverage changed')
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,
              requirements=[dict(id='R'+str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks),1)])
    (out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('staging inputs changed')
    return out/'plan.json'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','official','energyplus'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--negative',action='store_true');a=p.parse_args()
    plan=stage(a.out,a.official,a.negative)
    result=execute(plan,plan.parent/'run',energyplus=a.energyplus.resolve())
    (plan.parent/'diagnosis.json').write_text(json.dumps(diagnose(plan,plan.parent/'run'),indent=2),encoding='utf-8')
    print(json.dumps(result['tasks'],indent=2))
    return 0 if result['execution_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
