"""Fixed JSON-only worker for MCP calls; no protocol threads/native imports mix."""
import contextlib
import importlib
import json
import os
from pathlib import Path
import sys
from .cli import digest
from .module_contract import read_json


def read_source_plan(plan):
    from . import workflow
    path=Path(plan).resolve();source=read_json(path);before=digest(path)
    documents=workflow.plan_documents(path.parent,source)
    if digest(path)!=before:raise ValueError('Plan changed during source reading')
    return dict(plan=source,plan_sha256=before,documents=documents,semantic_completeness='not_assessed',design_accepted=False)


# Fixed allowlist of trusted operations. Resolve only the
# selected module inside the worker, never import every optional native engine
# to initialize the protocol or perform an unrelated read.
OPERATIONS=frozenset('bsa.'+module+'.'+name for module,names in {
    'project_start':'start', 'engineering_handoff':'template run verify',
    'workflow':'execute', 'workflow_status':'diagnose', 'source_page':'run',
    'visual_transcription':'prepare', 'source_review':'run',
    'reference_library':'catalogue read', 'pump_catalogue_iteration':'run verify',
    'artifact_access':'index read render_page', 'delivery':'template assess',
    'recovery_controller':'run verify', 'hvac_package_access':'prepare run inspect',
    'mcp_worker':'read_source_plan',
    'network_analysis_access':'run_network run_fittings inspect list_requests read_request run_delivery inspect_delivery',
    'tag_delivery_access':'run inspect',
    'pressure_ledger_access':'run inspect list_gaps read_outlet',
    'drawing_access':'run inspect',
    'revit_connectivity':'run',
    'revit_automation_reopen':'verify',
    'revit_request':'prepare',
    'fds_temperature':'run verify',
    'ifc_port_inventory':'run',
    'ifc_port_bcf':'run verify_export',
    'delivery_archive':'verify_archive',
    'changes.access':'checkpoint inspect',
}.items() for name in names.split())


def resolve(operation):
    if operation not in OPERATIONS:raise ValueError('Fixed registered engineering call required')
    module,name=operation.rsplit('.',1)
    return getattr(importlib.import_module(module),name)


def main(response_file=None):
    try:
        request=json.load(sys.stdin)
        if not isinstance(request,dict) or set(request)!={'operation','args','kwargs'} or request['operation'] not in OPERATIONS or not isinstance(request['args'],list) or not isinstance(request['kwargs'],dict):
            raise ValueError('Fixed registered engineering call required')
        if request['operation']=='bsa.workflow.execute':request['args']=[Path(p) for p in request['args']]
        options=request['kwargs'].get('execute_options',request['kwargs'])
        for key in ('energyplus','autocad','radiance_bin','ifcmcp_python','three_phase_python','graphviz','pdf2plot_python','honeybee_python'):
            if options.get(key) is not None:options[key]=Path(options[key])
        from .verification_scope import operation_scope
        with contextlib.redirect_stdout(sys.stderr),operation_scope(enabled=os.environ.get('BSA_DISABLE_AUDIT_MEMO')!='1'):
            value=resolve(request['operation'])(*request['args'],**request['kwargs'])
        result=dict(ok=True,value=value)
    except ModuleNotFoundError as exc:
        from .cli_errors import missing_dependency
        detail=missing_dependency(exc)
        result=dict(ok=False,error='ModuleNotFoundError: '+detail['message'],error_kind='missing_dependency',missing_module=detail['missing_module'],suggested_extra=detail['suggested_extra'])
    except Exception as exc:result=dict(ok=False,error=type(exc).__name__+': '+str(exc))
    encoded=json.dumps(result,ensure_ascii=False,allow_nan=False)
    if response_file is None:print(encoded)
    else:
        # This fresh private path is supplied by the parent, never by a document.
        # Native C/C++ stdout bypasses contextlib.redirect_stdout; keep results
        # on a dedicated channel instead of trying to parse mixed native logs.
        with Path(response_file).open('x',encoding='utf-8') as stream:stream.write(encoded)
    return 0 if result['ok'] else 2


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--response-file',type=Path)
    raise SystemExit(main(parser.parse_args().response_file))
