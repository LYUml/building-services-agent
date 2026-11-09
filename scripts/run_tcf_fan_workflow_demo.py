"""Stage the source-native fan research plan, then invoke the unified workflow CLI."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from bsa.cli import digest
ROOT=Path(__file__).resolve().parents[1]


def stage(out,pdf,extraction):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('new repository-local output required')
    out.mkdir(parents=True);ex=ROOT/'examples/rectangular-air'
    for name in ('elbow-chain-model.json','elbow-chain-binding.json'):shutil.copyfile(ex/name,out/name)
    p=json.loads((ex/'elbow-chain-project.json').read_text());p['sources']['research_duty']='Explicit synthetic 200 Pa fixed terminal total-pressure target; not measured building duty or regulation';p['nodes'][-1].update(required_total_pressure_pa=200,source='research_duty');(out/'project.json').write_text(json.dumps(p,indent=2))
    shutil.copyfile(pdf,out/'manufacturer.pdf');cache=out/'extraction';cache.mkdir()
    for name in ('extraction.json','disjoint-paths.json','calibrated.csv','export.log'):shutil.copyfile(Path(extraction)/name,cache/name)
    (out/'basis.json').write_text(json.dumps(dict(source='Research-only graph/native-path correspondence; explicit synthetic fan inlet 0 Pa reference; all manufacturer and installation uncertainty unresolved',speed_rpm=1450,inlet_total_pressure_pa=0),indent=2))
    paragraphs=['Author and independently verify the synthetic fixed-section rectangular lead, finite elbow and tail; retain true arc length, source K and pressure failures.',
                'Reopen the pinned TCF manufacturer graph and evaluate interpolation-only fan flow sensitivity on that exact native path; preserve source-domain and uncertainty blockers.',
                'Review source accuracy, actual fan and motor identity, installation, acoustics, controls and Hong Kong requirements before engineering acceptance.']
    brief=out/'brief.md';brief.write_text('\n\n'.join(paragraphs)+'\n')
    tasks=[dict(id='air',kind='rectangular_network_binding',project='project.json',model='elbow-chain-model.json',binding='elbow-chain-binding.json'),dict(id='research',kind='tcf_fan_research',depends_on='air',pdf='manufacturer.pdf',extraction='extraction/extraction.json',basis='basis.json'),dict(id='review',kind='manual',requires_pass=['air','research'],description=paragraphs[-1])]
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={f'P{i:03}':'requirement' for i in range(1,4)},tasks=tasks,requirements=[dict(id=f'R{i}',passage=f'P{i:03}',quote=q,task=t['id'],acceptance=q) for i,(q,t) in enumerate(zip(paragraphs,tasks),1)])
    path=out/'plan.json';path.write_text(json.dumps(plan,indent=2));return path


def run(out,pdf,extraction,pdf2plot_python=None):
    plan=stage(out,pdf,extraction);root=plan.parent
    command=[sys.executable,'-m','bsa.cli','workflow',str(plan),'--out',str(root/'workflow')]
    if pdf2plot_python:command.extend(['--pdf2plot-python',str(pdf2plot_python)])
    worker=subprocess.run(command,capture_output=True,text=True);(root/'worker.log').write_text(worker.stdout+worker.stderr,encoding='utf-8')
    if worker.returncode!=2 or not (root/'workflow/diagnosis.json').is_file():raise ValueError('expected pending research workflow and source-bound diagnosis')
    r=json.loads((root/'workflow/workflow.json').read_text());states={k:v['status'] for k,v in r['tasks'].items()}
    if states!={'air':'pass','research':'pending','review':'pending'}:raise ValueError('unexpected research execution states')
    result=dict(states=states,diagnosis_sha256=digest(root/'workflow/diagnosis.json'),design_accepted=False)
    (root/'demonstration.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','pdf','extraction'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--pdf2plot-python',type=Path)
    print(json.dumps(run(**vars(p.parse_args()))))
