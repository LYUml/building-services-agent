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
                    for name in ('bsa_run_native_network_delivery','bsa_inspect_native_network_delivery'):
                        self.assertFalse(tools[name].inputSchema['additionalProperties'])
                        self.assertNotIn('autocad',tools[name].inputSchema.get('properties',{}))
                    for args in [dict(source='missing',out='delivery'),dict(source='missing',out='delivery',autocad='override'),dict(source='missing',out='delivery',scale=True)]:
                        r=await session.call_tool('bsa_run_native_network_delivery',args);self.assertTrue(r.isError)
                    r=await session.call_tool('bsa_inspect_native_network_delivery',dict(out='../escape'));self.assertTrue(r.isError)
                    self.assertFalse((Path(folder)/'delivery').exists())
                    controls=[(names[0],dict(source='../escape',out='new')),
                        (names[1],dict(analysis='missing',basis='missing.json',out='new',python='override')),
                        (names[1],dict(analysis='missing',basis='../escape.json',out='new')),
                        (names[2],dict(out='../escape')),
                        (names[3],dict(out='missing'))]
                    for name,args in controls:
                        r=await session.call_tool(name,args);self.assertTrue(r.isError)
                    self.assertFalse((Path(folder)/'new').exists())
                    from tests.test_network_analysis_access import RecordedFittingAccessTests
                    _,sha=RecordedFittingAccessTests().fixture(Path(folder))
                    r=await session.call_tool('bsa_list_native_fitting_requests',dict(out='.',record_sha256=sha))
                    # The existing host path contract excludes the root itself.
                    self.assertTrue(r.isError)
                    child=Path(folder)/'record';child.mkdir()
                    (Path(folder)/'fitting-data.json').rename(child/'fitting-data.json')
                    r=await session.call_tool('bsa_list_native_fitting_requests',dict(out='record',record_sha256=sha,limit=2))
                    self.assertFalse(r.isError);self.assertEqual(len(r.structuredContent['requests']),2)
                    r=await session.call_tool('bsa_read_native_fitting_request',dict(out='record',record_sha256=sha,product_guid='same-body',inlet_port_guid='in',outlet_port_guid='17'))
                    self.assertFalse(r.isError);self.assertEqual(r.structuredContent['request']['outlet_port_guid'],'17')
                    for value in (True,'2',21,0):
                        r=await session.call_tool('bsa_list_native_fitting_requests',dict(out='record',record_sha256=sha,limit=value))
                        self.assertTrue(r.isError)
