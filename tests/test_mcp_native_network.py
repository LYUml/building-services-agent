import os
from pathlib import Path
import sys
import tempfile
import unittest


class NativeNetworkMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_protocol_schema_and_rejected_overrides(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'runs') as folder:
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server'],cwd=str(root),env={**os.environ,'BSA_PROJECT_ROOT':folder})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize();tools={t.name:t for t in (await session.list_tools()).tools}
                    names=('bsa_run_native_network_analysis','bsa_run_native_fitting_analysis',
                        'bsa_inspect_native_network_analysis','bsa_inspect_native_fitting_analysis')
                    for name in names:
                        self.assertFalse(tools[name].inputSchema['additionalProperties'])
                    controls=[(names[0],dict(source='../escape',out='new')),
                        (names[1],dict(analysis='missing',basis='missing.json',out='new',python='override')),
                        (names[1],dict(analysis='missing',basis='../escape.json',out='new')),
                        (names[2],dict(out='../escape')),
                        (names[3],dict(out='missing'))]
                    for name,args in controls:
                        r=await session.call_tool(name,args);self.assertTrue(r.isError)
                    self.assertFalse((Path(folder)/'new').exists())
