"""Revised IFC + fresh WSD capacity workflow with an insufficient-curve control."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.workflow import execute,passages,verify
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


def run(pdf,python,autocad,out):
    pdf,out=Path(pdf).resolve(),Path(out).resolve()
    pack=ROOT/'regulations/hk/plumbing-pumps-2026.11.09/pack.json'
    if digest(pdf)!=json.loads(pack.read_text())['sources']['wsd_tr_2026_04']['sha256']:raise ProjectError('pinned WSD PDF required')
    if not out.is_relative_to(ROOT) or out.exists() or out==pdf or out in pdf.parents:raise ProjectError('new repository output required')
    out.mkdir(parents=True);results={}
    for scenario in ('positive','weak_curve'):
        stage=out/scenario;stage.mkdir()
        plan=json.loads((ROOT/'examples/ifcmcp-analysis-plan.json').read_text())
        paths={plan['brief']}
        for task in plan['tasks']:
            paths.update(task[k] for k in ('project','model','binding','settings','patch','requirements') if k in task)
        for name in paths:
            target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'examples'/name,target)
        shutil.copyfile(pack,stage/'pack.json');shutil.copyfile(pdf,stage/'wsd-tr-2026-04.pdf')
        for name in ('binding.json','curve.json'):shutil.copyfile(ROOT/'examples/hk-plumbing-pumps'/name,stage/name)
        if scenario=='weak_curve':
            curve=json.loads((stage/'curve.json').read_text())
            for point in curve['points']:point['total_pressure_rise_pa']*=.1
            curve['sources'][curve['source']]='Synthetic weak curve negative control; no product evidence'
            (stage/'curve.json').write_text(json.dumps(curve,indent=2))
        brief=stage/plan['brief']
        brief.write_text(brief.read_text()+'\n\nRecompute pump operating capacity on the revised saved IFC route against the sourced tank outflow and pinned WSD rule. Keep duplication declarations, real equipment/controls and full regulatory conformity pending. A failed capacity check must block drawing and native plotting.\n',encoding='utf-8')
        row=passages(brief)[-1];plan['brief_sha256']=digest(brief);plan['passage_dispositions'][row['id']]='requirement'
        task=dict(id='capacity',kind='plumbing_pump_regulations',depends_on='hydraulics',curve='curve.json',basis='binding.json',pack='pack.json',sources='.')
        plan['tasks'].insert(5,task)
        plan['tasks'][6]['requires_pass'].append('capacity')
        plan['requirements'].append(dict(id='capacity',task='capacity',passage=row['id'],quote=row['text'],acceptance=row['text']))
        file=stage/'plan.json';file.write_text(json.dumps(plan,indent=2))
        result=execute(file,stage/'workflow',ifcmcp_python=python,autocad=autocad)
        statuses={k:v['status'] for k,v in result['tasks'].items()}
        expected=['pass']*8 if scenario=='positive' else ['pass']*5+['fail','pending','pending']
        results[scenario]=dict(statuses=statuses,integrity=verify(stage/'workflow'),expected_behavior_pass=list(statuses.values())==expected)
    result=dict(scenarios=results,demonstration_checks_pass=all(v['expected_behavior_pass'] and v['integrity']['integrity_pass'] for v in results.values()),design_accepted=False)
    (out/'summary.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('wsd-pdf','ifcmcp-python','autocad','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=run(a.wsd_pdf,a.ifcmcp_python,a.autocad,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['demonstration_checks_pass'] else 2)
