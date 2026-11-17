"""Audit the actual SDK catalogue against source routes; executes no engineering."""
import argparse
import ast
import asyncio
import hashlib
import json
from pathlib import Path
import sys

from bsa import mcp_server,workspace
from bsa.mcp_worker import OPERATIONS


async def audit():
    source=Path(mcp_server.__file__)
    tree=ast.parse(source.read_text(encoding='utf-8'))
    routes={};all_operations=set()
    for node in ast.walk(tree):
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
        decorators=[d.func.attr for d in node.decorator_list
                    if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute)]
        operations=sorted({call.args[0].value for call in ast.walk(node)
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Name)
            and call.func.id=='invoke' and call.args and isinstance(call.args[0],ast.Constant)})
        all_operations.update(operations)
        if 'tool' in decorators:routes[node.name]=operations
    if all_operations!=OPERATIONS:raise ValueError('MCP routes and fixed worker whitelist differ')
    server=mcp_server.create_server()
    tools=await server.list_tools()
    if {tool.name for tool in tools}!=set(routes):raise ValueError('SDK tool catalogue differs from source declarations')
    rows=[]
    for tool in tools:
        schema=tool.inputSchema
        if schema.get('additionalProperties') is not False:raise ValueError('Tool permits unknown top-level fields')
        forbidden={'autocad','energyplus','radiance_bin','pdftoppm','report_font','execute_options','command','executable','python'}
        if forbidden.intersection(schema.get('properties',{})):raise ValueError('Tool accepts host executable override')
        if not routes[tool.name] and tool.name!='bsa_save_json':raise ValueError('Unmapped direct tool needs explicit review')
        if tool.annotations is None or tool.annotations.destructiveHint is not False:raise ValueError('Tool mutation contract missing')
        try:
            await server.call_tool(tool.name,{'__bsa_contract_unknown__':True})
        except ValueError as exc:
            if 'Unknown tool argument fields' not in str(exc):raise
        else:raise ValueError('Unknown field reached tool dispatch')
        rows.append(dict(name=tool.name,worker_operations=routes[tool.name],
            read_only=tool.annotations.readOnlyHint,description=tool.description,
            input_schema=schema))
    return dict(schema='bsa.mcp-contract-audit/1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        python=sys.version.split()[0],sdk_version=mcp_server.SDK_VERSION,
        tools=rows,tool_count=len(rows),worker_operation_count=len(OPERATIONS),
        exact_route_coverage=True,unknown_fields_rejected=True,host_runtime_fields_excluded=True,
        direct_operation='bsa_save_json: fresh declarative JSON only; downstream validation required',
        scope='SDK catalogue, source routes and actual unknown-field rejection; no valid engineering calls, UI connection or native execution',
        design_accepted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    out=Path(parser.parse_args().out).resolve()
    if not out.is_relative_to(workspace.ROOT/'runs') or out.exists():raise ValueError('Fresh repository runs output required')
    result=asyncio.run(audit());out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k!='tools'},indent=2))
