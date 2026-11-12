"""Fixed JSON-only worker for MCP calls; no protocol threads/native imports mix."""
import contextlib
import json
from pathlib import Path
import sys
from . import engineering_handoff,project_start,workflow,workflow_status,source_page,visual_transcription,source_review,reference_library,pump_catalogue_iteration,artifact_access
from .cli import digest
from .module_contract import read_json


def read_source_plan(plan):
    path=Path(plan).resolve();source=read_json(path);before=digest(path)
    documents=workflow.plan_documents(path.parent,source)
    if digest(path)!=before:raise ValueError('Plan changed during source reading')
    return dict(plan=source,plan_sha256=before,documents=documents,semantic_completeness='not_assessed',design_accepted=False)


OPERATIONS={function.__module__+'.'+function.__name__:function for function in
    (project_start.start,engineering_handoff.template,engineering_handoff.run,engineering_handoff.verify,
     workflow.execute,workflow_status.diagnose,source_page.run,visual_transcription.prepare,source_review.run,reference_library.catalogue,reference_library.read,
     pump_catalogue_iteration.run,pump_catalogue_iteration.verify,artifact_access.index,artifact_access.read)}
OPERATIONS['bsa.mcp_worker.read_source_plan']=read_source_plan


def main():
    try:
        request=json.load(sys.stdin)
        if not isinstance(request,dict) or set(request)!={'operation','args','kwargs'} or request['operation'] not in OPERATIONS or not isinstance(request['args'],list) or not isinstance(request['kwargs'],dict):
            raise ValueError('Fixed registered engineering call required')
        if request['operation']=='bsa.workflow.execute':request['args']=[Path(p) for p in request['args']]
        options=request['kwargs'].get('execute_options',request['kwargs'])
        for key in ('energyplus','autocad','radiance_bin','ifcmcp_python','three_phase_python','graphviz','pdf2plot_python','honeybee_python'):
            if options.get(key) is not None:options[key]=Path(options[key])
        with contextlib.redirect_stdout(sys.stderr):value=OPERATIONS[request['operation']](*request['args'],**request['kwargs'])
        result=dict(ok=True,value=value)
    except Exception as exc:result=dict(ok=False,error=type(exc).__name__+': '+str(exc))
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))
    return 0 if result['ok'] else 2


if __name__=='__main__':raise SystemExit(main())
