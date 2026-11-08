"""Stage and run a synthetic shared LPD + IES/Radiance workflow in this repository."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,passages
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


def stage(out,official,high_target=False):
    out=Path(out).resolve();official=Path(official).resolve()
    pack=ROOT/'regulations/hk/lighting-2026.11.08/pack.json'
    metadata=json.loads(pack.read_text())['sources']['emsd_bec_2024']
    if not official.is_file() or digest(official)!=metadata['sha256']:raise ProjectError('download the pinned BEC PDF before staging')
    inputs={ROOT/'examples/office-electrical/project.json':'project.json',ROOT/'examples/office-electrical/geometry.json':'geometry.json',
            ROOT/'examples/regulations-hk-lighting/shared-space-basis.json':'basis.json',pack:'pack.json',
            ROOT/'examples/shared-lighting.json':'optical.json',ROOT/'examples/lighting/synthetic-1000cd.ies':'lighting/synthetic-1000cd.ies',official:metadata['cache_filename']}
    if out==ROOT or not out.is_relative_to(ROOT) or any(out==p or out in p.parents for p in inputs):raise ProjectError('new staging directory must be inside this repository and separate from sources')
    before={str(p):digest(p) for p in inputs}
    out.mkdir(parents=True,exist_ok=False)
    for src,name in inputs.items():
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        if digest(dest)!=before[str(src)]:raise ProjectError('staged source copy differs')
    if high_target:
        p=out/'optical.json';data=json.loads(p.read_text());data['targets']['average_lux']=1000
        data['sources']['high-target']='Explicit synthetic negative control: supplied sensor mean target raised to 1000 lx; not a code threshold'
        data['targets']['source']='high-target';p.write_text(json.dumps(data,indent=2),encoding='utf-8')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('staging source changed')
    brief=out/'brief.md'
    brief.write_text('Check the shared office lighting power density with the pinned Hong Kong pack.\n\nRun shared CAD/IFC and real IES-backed Radiance checks only after the selected LPD check passes.\n\nReview actual geometry, photometry, daylight, glare, controls and full engineering acceptance separately.',encoding='utf-8')
    rows=passages(brief)
    tasks=[dict(id='lpd',kind='lighting_regulations',project='project.json',geometry='geometry.json',basis='basis.json',pack='pack.json',sources='.'),
           dict(id='lighting',kind='electrical_lighting',project='project.json',geometry='geometry.json',optical='optical.json',requires_pass=['lpd']),
           dict(id='review',kind='manual',requires_pass=['lighting'],description='Actual geometry/photometry/controls/glare and full engineering acceptance pending')]
    if len(rows)!=len(tasks):raise ProjectError('demo brief passage coverage changed')
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,
              requirements=[dict(id='R'+str(i+1),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
    (out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    (out/'staging.json').write_text(json.dumps(dict(original_inputs=before,inputs_unchanged=True,high_target_control=high_target,
        staged_files={name:digest(out/name) for name in inputs.values()}),indent=2),encoding='utf-8')
    return out/'plan.json'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--official',type=Path,required=True);p.add_argument('--radiance-bin',type=Path,required=True)
    p.add_argument('--high-target',action='store_true');a=p.parse_args()
    plan=stage(a.out,a.official,a.high_target);r=execute(plan,plan.parent/'run',radiance_bin=a.radiance_bin.resolve())
    (plan.parent/'diagnosis.json').write_text(json.dumps(diagnose(plan,plan.parent/'run'),indent=2),encoding='utf-8')
    print(json.dumps(r['tasks'],indent=2))
    return 0 if r['execution_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
