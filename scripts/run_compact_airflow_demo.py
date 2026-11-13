"""Execute the existing public saved-IFC airflow graph with current authoring."""
import argparse
import json
from pathlib import Path
import time
from bsa import workflow,workflow_status
from bsa.workspace import ROOT


def run(out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('Fresh public demo output required')
    out.mkdir(parents=True);plan=ROOT/'examples/route-search/port-airflow-state-plan.json'
    start=time.perf_counter();workflow.execute(plan,out/'workflow');elapsed=time.perf_counter()-start
    diagnosis=workflow_status.diagnose(plan,out/'workflow')
    result=dict(elapsed_seconds=elapsed,diagnosis=diagnosis,design_accepted=False,scope='Existing public circular air graph only; no native DWG plot or installation acceptance')
    (out/'execution.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(seconds=elapsed,tasks={t['id']:t['status'] for t in diagnosis['tasks']},design_accepted=False),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);run(parser.parse_args().out)
