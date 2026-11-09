"""Workflow adapter for the official MCP source-bound pump metadata operation."""
import json
from pathlib import Path
import subprocess
from .cli import digest
from .engine import ProjectError


def run(ifc,patch,out,python):
    ifc,patch,out,python=[Path(p).resolve() for p in (ifc,patch,out,python)]
    root=Path(__file__).resolve().parents[2]
    script=root/'scripts/ifcmcp_pump_properties.py'
    inputs={str(p):digest(p) for p in (ifc,patch,script,root/'scripts/probe_ifcmcp.py',python)}
    if any(out==Path(p) or out in Path(p).parents for p in inputs):raise ProjectError('output must not contain source inputs')
    out.mkdir(parents=True,exist_ok=False)
    with (out/'process.log').open('wb') as log:
        proc=subprocess.run([str(python),str(script),'--model',str(ifc),'--patch',str(patch),'--out',str(out/'native')],stdout=log,stderr=subprocess.STDOUT,timeout=90)
    report=out/'native/edit-checks.json';model=out/'native/model.ifc'
    if proc.returncode or not report.is_file() or not model.is_file():raise ProjectError('MCP metadata edit failed; inspect process.log')
    result=json.loads(report.read_text(encoding='utf-8'))
    expected={n:'0.9.0' for n in ('ifcopenshell-mcp','ifcopenshell','ifcquery','ifcedit','ifc5d')};expected['mcp']='1.26.0'
    if result.get('runtime')!=expected:raise ProjectError('MCP metadata runtime differs from verified pins')
    if result.get('inputs')!={str(p):inputs[str(p)] for p in (ifc,patch)}:raise ProjectError('MCP metadata input identity differs')
    if result.get('property_edit_checks_pass') is not True or result.get('model_sha256')!=digest(model):raise ProjectError('MCP metadata saved checks failed')
    if any(digest(Path(p))!=h for p,h in inputs.items()):raise ProjectError('MCP metadata source inputs changed')
    result=dict(inputs=inputs,calculated_checks_pass=True,model_sha256=digest(model),native_report_sha256=digest(report),
                design_accepted=False,scope=result['scope'])
    (out/'metadata-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
