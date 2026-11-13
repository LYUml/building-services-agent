"""Run a declared recovery policy through the actual local SDK stdio transport."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]

async def run(args):
    root=Path(args.project_root).resolve()
    if not root.is_dir():raise ValueError('Existing public/project workspace required')
    receipt=(root/args.receipt).resolve()
    if not receipt.is_relative_to(root) or receipt.exists():raise ValueError('Fresh project-local receipt required')
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','bsa.mcp_server'],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root),'PYTHONUTF8':'1'})
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            result=await session.call_tool('bsa_run_recovery',dict(plan=args.plan,original_run=args.original_run,policy=args.policy,out=args.out))
            if result.isError:raise ValueError(str(result.content))
            checked=await session.call_tool('bsa_verify_recovery',dict(out=args.out))
            if checked.isError:raise ValueError(str(checked.content))
            record=dict(recovery=result.structuredContent,verification=checked.structuredContent,design_accepted=False)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    with receipt.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
    print(json.dumps(record['verification'],indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['project-root','plan','original-run','policy','out','receipt']:parser.add_argument('--'+key,required=True)
    asyncio.run(run(parser.parse_args()))
