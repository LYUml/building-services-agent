"""Read-only protocol trial of the pinned upstream IfcMCP in its isolated runtime."""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import ifcopenshell
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def run(model, out):
    model, out = Path(model).resolve(), Path(out).resolve()
    before = digest(model)
    if out.exists() or out == model or out in model.parents:
        raise ValueError('new output separate from model required')
    out.mkdir(parents=True)
    records = {}
    params = StdioServerParameters(command=sys.executable, args=['-m','ifcmcp'])
    with (out/'server.log').open('w',encoding='utf-8') as errors:
        async with stdio_client(params,errlog=errors) as (read,write):
            async with ClientSession(read,write) as session:
                records['initialize']=(await session.initialize()).model_dump(mode='json')
                records['tools']=(await session.list_tools()).model_dump(mode='json')
                for label,name,args in (
                    ('unloaded','ifc_summary',{}),
                    ('load','ifc_load',{'path':str(model)}),
                    ('summary','ifc_summary',{}),
                    ('pumps','ifc_select',{'query':'IfcPump'}),
                    ('pipes','ifc_select',{'query':'IfcPipeSegment'}),
                    ('tree','ifc_tree',{}),
                    ('reset','ifc_reset',{}),
                    ('after_reset','ifc_summary',{})):
                    records[label]=(await session.call_tool(name,args)).model_dump(mode='json')
    native=ifcopenshell.open(str(model))
    expected={label:{(e.id(),e.is_a(),e.Name) for e in native.by_type(cls)}
              for label,cls in (('pumps','IfcPump'),('pipes','IfcPipeSegment'))}
    checks={'unloaded_rejected':records['unloaded']['isError'] is True,
            'reset_rejected':records['after_reset']['isError'] is True,
            'queries_succeeded':all(records[k]['isError'] is False for k in ('load','summary','pumps','pipes','tree','reset')),
            'source_unchanged':digest(model)==before}
    summary=records['summary'].get('structuredContent') or {}
    checks['summary_matches_saved_model']=summary.get('schema')==native.schema and summary.get('total_entities')==sum(1 for _ in native)
    for label in expected:
        rows=(records[label].get('structuredContent') or {}).get('result',[])
        checks[label+'_match_saved_model']={(r['id'],r['type'],r['name']) for r in rows}==expected[label]
    result=dict(checks=checks,protocol_checks_pass=all(checks.values()),model=str(model),model_sha256=before,source_unchanged=digest(model)==before,
                runtime={n:importlib.metadata.version(n) for n in ('ifcopenshell-mcp','ifcopenshell','ifcquery','ifcedit','ifc5d','mcp')},
                calls=records,design_accepted=False,
                scope='Read-only MCP protocol trial; no editing, geometry, drawings or regulatory acceptance')
    (out/'trial.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args()
    result=asyncio.run(asyncio.wait_for(run(args.model,args.out),timeout=60))
    print(json.dumps({k:v for k,v in result.items() if k!='calls'},indent=2))
    raise SystemExit(0 if result['protocol_checks_pass'] else 2)
