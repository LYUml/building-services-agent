import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import timedelta
import unittest

ROOT=Path(__file__).resolve().parents[1]
AUTOCAD=Path('C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe')


@unittest.skipUnless(importlib.util.find_spec('mcp'),'MCP SDK required')
class MCPDrawingTests(unittest.IsolatedAsyncioTestCase):
    async def test_protocol_inspection_host_boundary_and_forged_drawing(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        from bsa.drawing_document import run
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);project=root/'drawing.json';shutil.copyfile(ROOT/'examples/drawing-document.json',project)
            run(project,root/'dxf-only')
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server'],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    tools=(await session.list_tools()).tools;self.assertIn('bsa_draw_document',{t.name for t in tools})
                    result=await session.call_tool('bsa_inspect_drawing_document',{'project':'drawing.json','out':'dxf-only'})
                    self.assertFalse(result.isError,str(result));self.assertTrue(result.structuredContent['integrity_pass']);self.assertFalse(result.structuredContent['native_reopen_pass'])
                    for args in [{'project':'drawing.json','out':'native'},{'project':'../outside.json','out':'escape'},{'project':'drawing.json','out':'override','autocad':'evil.exe'}]:
                        response=await session.call_tool('bsa_draw_document',args);self.assertTrue(response.isError)
                    self.assertFalse((root/'native').exists());self.assertFalse((root/'override').exists())
                    (root/'dxf-only/Drawing.dxf').write_text('corrupt')
                    response=await session.call_tool('bsa_inspect_drawing_document',{'project':'drawing.json','out':'dxf-only'});self.assertTrue(response.isError)

    @unittest.skipUnless(AUTOCAD.is_file(),'Explicit installed AutoCAD required')
    async def test_actual_native_protocol_roundtrip(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);shutil.copyfile(ROOT/'examples/drawing-document.json',root/'drawing.json')
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server','--autocad',str(AUTOCAD)],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    response=await session.call_tool('bsa_draw_document',{'project':'drawing.json','out':'native'},read_timeout_seconds=timedelta(seconds=180))
                    self.assertFalse(response.isError,str(response));r=response.structuredContent
                    self.assertTrue(r['integrity_pass']);self.assertTrue(r['native_reopen_pass']);self.assertEqual(r['editable_entities']['entity_types']['DIMENSION'],3);self.assertFalse(r['design_accepted'])
                    inspected=await session.call_tool('bsa_inspect_drawing_document',{'project':'drawing.json','out':'native'})
                    self.assertFalse(inspected.isError,str(inspected));self.assertEqual(inspected.structuredContent,r)


if __name__=='__main__':unittest.main()
