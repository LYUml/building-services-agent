"""Run the pinned official IFC MCP inventory in its isolated Python runtime."""
import json
from pathlib import Path
import subprocess
from .cli import digest
from .engine import ProjectError


def validate(contract):
    if not isinstance(contract,dict) or set(contract)!={'source','minimum_counts'} or not isinstance(contract['source'],str) or not contract['source'].strip():
        raise ProjectError('sourced IFC inventory requirements required')
    counts=contract['minimum_counts']
    if not isinstance(counts,dict) or not counts or any(k not in ('IfcPump','IfcPipeSegment','IfcPipeFitting','IfcDuctSegment','IfcDuctFitting','IfcDistributionPort','IfcDistributionSystem') or type(v) is not int or v<1 for k,v in counts.items()):
        raise ProjectError('positive minimum supported MEP class counts required')


def run(ifc,requirements,out,python):
    ifc,requirements,out,python=[Path(p).resolve() for p in (ifc,requirements,out,python)]
    script=Path(__file__).resolve().parents[2]/'scripts/probe_ifcmcp.py'
    contract=json.loads(requirements.read_text(encoding='utf-8-sig'));validate(contract)
    inputs={str(p):digest(p) for p in (ifc,requirements,script,python)}
    if any(out==Path(p) or out in Path(p).parents for p in inputs):raise ProjectError('output must not contain inputs')
    out.mkdir(parents=True,exist_ok=False)
    with (out/'process.log').open('wb') as log:
        proc=subprocess.run([str(python),str(script),'--model',str(ifc),'--out',str(out/'protocol')],stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if proc.returncode or not (out/'protocol/trial.json').is_file():raise ProjectError('IFC MCP query failed; inspect process.log')
    trial=json.loads((out/'protocol/trial.json').read_text(encoding='utf-8'))
    expected={n:'0.9.0' for n in ('ifcopenshell-mcp','ifcopenshell','ifcquery','ifcedit','ifc5d')};expected['mcp']='1.26.0'
    if trial.get('runtime')!=expected:raise ProjectError('IFC MCP runtime versions differ from verified pins')
    if trial.get('model')!=str(ifc) or trial.get('model_sha256')!=inputs[str(ifc)]:raise ProjectError('IFC MCP source identity mismatch')
    if not trial.get('protocol_checks_pass') or not trial.get('source_unchanged'):raise ProjectError('IFC MCP protocol verification failed')
    counts=trial['calls']['summary']['structuredContent']['types']
    checks=[dict(ifc_class=k,minimum=v,actual=counts.get(k,0),passed=counts.get(k,0)>=v) for k,v in contract['minimum_counts'].items()]
    if any(digest(Path(p))!=h for p,h in inputs.items()):raise ProjectError('IFC MCP inputs changed during execution')
    result=dict(inputs=inputs,source=contract['source'],count_checks=checks,calculated_checks_pass=all(c['passed'] for c in checks),
                protocol_report_sha256=digest(out/'protocol/trial.json'),runtime=trial['runtime'],design_accepted=False,
                scope='Saved IFC inventory and minimum class counts only; not geometry, equipment identity or engineering acceptance')
    (out/'ifc-query.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
