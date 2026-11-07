"""Read-only MCP integration probe against a generated OSM, scoped to this workspace."""
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    root=Path(__file__).resolve().parents[1]
    model=Path(sys.argv[1]).resolve()
    if not model.is_relative_to(root):raise ValueError("model must be in this workspace")
    output=root/"runs/mcp-probe"
    output.mkdir(exist_ok=True)
    env=dict(os.environ,OPENSTUDIO_MCP_RUN_ROOT=str(output),OPENSTUDIO_MCP_INPUT_ROOT=str(model.parent),
        OPENSTUDIO_MCP_MEASURES_DIR=str(output/"measures"),OSMCP_ENABLE_CODE_TOOLS="false",
        OSMCP_TOOLS_ALLOW="load_osm_model,get_building_info,list_thermal_zones,list_spaces")
    params=StdioServerParameters(command=sys.executable,args=["-m","mcp_server.server"],env=env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            catalog=await session.list_tools()
            results={"tools":[t.name for t in catalog.tools]}
            for name,args in (("load_osm_model",{"osm_path":str(model)}),("list_spaces",{}),("list_thermal_zones",{})):
                response=await session.call_tool(name,args)
                if response.isError or (response.structuredContent and response.structuredContent.get("ok") is False):raise RuntimeError(str(response))
                results[name]=response.model_dump(mode="json")
    (output/"probe.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print(json.dumps(results,indent=2))

asyncio.run(main())
