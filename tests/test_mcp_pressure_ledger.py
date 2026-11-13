import os
import sys
import tempfile
import unittest
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from tests import test_pressure_ledger_access as fixtures


class PressureLedgerProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_protocol_reads_schema_and_workspace_runtime_controls(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'runs') as folder:
            _,_,sha=fixtures.LedgerAccessTests().fixture(folder)
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server'],cwd=str(root),env={**os.environ,'BSA_PROJECT_ROOT':folder})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize();tools={t.name:t for t in (await session.list_tools()).tools}
                    names=['bsa_run_pressure_evidence_ledger','bsa_inspect_pressure_evidence_ledger','bsa_list_pressure_evidence_gaps','bsa_read_outlet_pressure_evidence']
                    for name in names:self.assertFalse(tools[name].inputSchema['additionalProperties'])
                    controls=[(names[0],dict(source='../escape',out='new')),(names[0],dict(source='missing',out='new',python='override')),(names[1],dict(out='../escape')),(names[2],dict(out='ledger',record_sha256=sha,limit=True))]
                    for name,args in controls:
                        r=await session.call_tool(name,args);self.assertTrue(r.isError)
                    self.assertFalse((Path(folder)/'new').exists())
                    r=await session.call_tool(names[2],dict(out='ledger',record_sha256=sha,limit=1));self.assertFalse(r.isError);self.assertEqual(r.structuredContent['total'],1)
                    r=await session.call_tool(names[3],dict(out='ledger',record_sha256=sha,outlet_port_guid='b'));self.assertFalse(r.isError);self.assertIsNone(r.structuredContent['fan_duty_Pa']);self.assertFalse(r.structuredContent['design_accepted'])
