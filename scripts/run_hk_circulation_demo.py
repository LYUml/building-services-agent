"""Reproduce synthetic thermal/HK pipe-rule workflows and expected blocking cases."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, verify
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]
CASES={
    'passing':('project-65mm.json','regulatory-bases-65mm.json','thermal-duty.json',{'duty':'pass','rules':'pass','water':'pass','review':'pending'}),
    'pipe-review':('project.json','regulatory-bases.json','thermal-duty.json',{'duty':'pass','rules':'pending','water':'pending','review':'pending'}),
    'insufficient-duty':('project-65mm.json','regulatory-bases-65mm.json','thermal-duty-insufficient.json',{'duty':'fail','rules':'pending','water':'pending','review':'pending'}),
}


def stage(out,official,case):
    out=Path(out).resolve();official=Path(official).resolve()
    if case not in CASES:raise ProjectError('unknown circulation demo case')
    pack=ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json'
    metadata=json.loads(pack.read_text())['sources']['emsd_bec_2024']
    if not official.is_file() or digest(official)!=metadata['sha256']:raise ProjectError('download pinned BEC PDF before staging')
    project,basis,duty,_=CASES[case];ex=ROOT/'examples/hvac-circulation'
    inputs={ex/project:'project.json',ex/basis:'basis.json',ex/duty:'thermal-duty.json',pack:'pack.json',official:metadata['cache_filename']}
    if out==ROOT or not out.is_relative_to(ROOT) or any(out==p or out in p.parents for p in inputs):
        raise ProjectError('new staging directory must be inside repository and separate from inputs')
    before={str(p):digest(p) for p in inputs}
    out.mkdir(parents=True,exist_ok=False)
    for src,name in inputs.items():
        shutil.copy2(src,out/name)
        if digest(out/name)!=before[str(src)]:raise ProjectError('staged input differs')
    brief=out/'brief.md'
    brief.write_text('Synthetic demonstration: verify sourced thermal transport targets.\n\nCheck scoped Hong Kong air-conditioning water pipe rules.\n\nRelease the same hydraulic scenario only after both checks pass.\n\nReview actual fluid conditions, equipment heat transfer, IFC correspondence, controls and complete engineering acceptance.',encoding='utf-8')
    tasks=[dict(id='duty',kind='circulation_duty',project='project.json',basis='thermal-duty.json'),
           dict(id='rules',kind='epanet_pipe_regulations',project='project.json',basis='basis.json',pack='pack.json',sources='.',requires_pass=['duty']),
           dict(id='water',kind='water_network',project='project.json',requires_pass=['rules']),
           dict(id='review',kind='manual',requires_pass=['water'],description='Actual engineering and complete regulatory acceptance unresolved')]
    rows=passages(brief)
    if len(rows)!=len(tasks):raise ProjectError('brief passage coverage changed')
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,
              requirements=[dict(id='R'+str(i+1),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
    (out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('source changed while staging')
    (out/'staging.json').write_text(json.dumps(dict(case=case,original_inputs=before,staged_files={name:digest(out/name) for name in inputs.values()}),indent=2),encoding='utf-8')
    return out/'plan.json'


def run_suite(out,official):
    out=Path(out).resolve()
    if out.exists():raise ProjectError('refusing to overwrite demo suite')
    results={}
    for case,(_,_,_,expected) in CASES.items():
        plan=stage(out/case,official,case)
        result=execute(plan,plan.parent/'run')
        integrity=verify(plan.parent/'run')
        (plan.parent/'diagnosis.json').write_text(json.dumps(diagnose(plan,plan.parent/'run'),indent=2),encoding='utf-8')
        statuses={k:v['status'] for k,v in result['tasks'].items()}
        # A blocked downstream task must not have executed a native solver.
        blocked=(['rules'] if expected['duty']=='fail' else [])+(['water'] if expected['water']=='pending' else [])
        blocked_absent=all(not (plan.parent/'run'/task).exists() for task in blocked)
        results[case]=dict(statuses=statuses,expected=expected,integrity_pass=integrity['integrity_pass'],blocked_outputs_absent=blocked_absent,
                           observed_expected_behavior=statuses==expected and integrity['integrity_pass'] and blocked_absent,
                           design_accepted=result['design_accepted'])
    summary=dict(cases=results,demonstration_verified=all(r['observed_expected_behavior'] and not r['design_accepted'] for r in results.values()),design_accepted=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path);parser.add_argument('--official',required=True,type=Path)
    args=parser.parse_args();result=run_suite(args.out,args.official)
    print(json.dumps(result,indent=2));return 0 if result['demonstration_verified'] else 2


if __name__=='__main__':raise SystemExit(main())
