"""Trial official IfcMCP 2D plots; retain native images and source hashes."""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from probe_ifcmcp import digest


async def run(model,cairo,out):
    model,cairo,out=[Path(p).resolve() for p in (model,cairo,out)]
    if not out.is_relative_to(Path(__file__).resolve().parents[1]) or out.exists() or out==model or out in model.parents:raise ValueError('new output separate from model required')
    before=digest(model);out.mkdir(parents=True);records={}
    params=StdioServerParameters(command=sys.executable,args=['-m','ifcmcp'],env=dict(os.environ,CAIROCFFI_DLL_DIRECTORIES=str(cairo)))
    with (out/'server.log').open('w',encoding='utf-8') as errors:
        async with stdio_client(params,errlog=errors) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                loaded=await session.call_tool('ifc_load',{'path':str(model)})
                if loaded.isError:raise ValueError(str(loaded))
                for view in ('floorplan','elevation'):
                    args=dict(selector='IfcPump, IfcPipeSegment',view=view,width_mm=210.,height_mm=297.,scale=.02,
                              png_width=840,png_height=1188,output_path=str(out/(view+'.svg')))
                    response=await session.call_tool('ifc_plot',args)
                    metadata=response.model_dump(mode='json')
                    for i,content in enumerate(metadata['content']):
                        if content['type']=='image':
                            image=out/(view+f'-{i}.png');image.write_bytes(base64.b64decode(content.pop('data')))
                            content['artifact']=image.name;content['sha256']=digest(image)
                    records[view]=dict(arguments=args,response=metadata)
                    (out/'calls.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    result=dict(model=str(model),model_sha256=before,source_unchanged=digest(model)==before,
                cairo_dll_sha256=digest(cairo/'cairo.dll'),calls=records,design_accepted=False,
                scope='Native plot trial; image review, coverage, dimensions and engineering acceptance are separate')
    (out/'trial.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','cairo','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=asyncio.run(asyncio.wait_for(run(a.model,a.cairo,a.out),60))
    print(json.dumps({k:dict(isError=v['response']['isError'],content=v['response']['content']) for k,v in r['calls'].items()},indent=2))
    raise SystemExit(2 if not r['source_unchanged'] or any(v['response']['isError'] for v in r['calls'].values()) else 0)
