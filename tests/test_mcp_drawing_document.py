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
    @unittest.skipUnless(AUTOCAD.is_file() and importlib.util.find_spec('textalloc'),'AutoCAD and pinned textalloc required')
    async def test_actual_native_label_allocation_protocol(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);shutil.copyfile(ROOT/'examples/drawing-labels.json',root/'labels.json')
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server','--autocad',str(AUTOCAD)],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    args={'project':'labels.json','out':'labels'}
                    response=await session.call_tool('bsa_draw_document',args,read_timeout_seconds=timedelta(seconds=180))
                    self.assertFalse(response.isError,str(response));r=response.structuredContent
                    self.assertTrue(r['native_reopen_pass']);self.assertEqual(r['label_placement']['labels'],3);self.assertFalse(r['design_accepted'])
                    self.assertGreaterEqual(r['label_placement']['protected_source_text_boxes'],1)
                    inspected=await session.call_tool('bsa_inspect_drawing_document',args)
                    self.assertFalse(inspected.isError,str(inspected));self.assertEqual(inspected.structuredContent,r)
                    for artifact in r['artifacts']:self.assertTrue((root/'labels'/artifact['path']).is_file())

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
                    import ezdxf
                    from bsa.cli import digest
                    doc=ezdxf.readfile(root/'native/reopened/source-export.dxf')
                    label=next(e for e in doc.modelspace().query('TEXT') if e.dxf.text=='PLAN')
                    reference=next(e for e in doc.modelspace().query('LINE') if e.dxf.layer=='BSA_DOC_REFERENCE')
                    recipe={'schema':'bsa.drawing-revision/1','source':'Synthetic existing-DWG edit control','drawing':'native/Drawing.dwg','drawing_sha256':digest(root/'native/Drawing.dwg'),
                            'edits':[{'handle':label.dxf.handle,'expected':{'text':'PLAN','layer':label.dxf.layer,'insert':list(label.dxf.insert)[:2]},'replacement':{'text':'PLAN REVIEWED','insert':list(label.dxf.insert)[:2]}}],
                            'sheet':{'source':'Original test sheet','paper':'A4','window_drawing_units':[0,0,290,200],'scale_denominator':1,'reference_handle':reference.dxf.handle,'pdf_tolerance_mm':.2}}
                    (root/'revision.json').write_text(json.dumps(recipe))
                    changed=await session.call_tool('bsa_draw_document',{'project':'revision.json','out':'revision'},read_timeout_seconds=timedelta(seconds=180))
                    self.assertFalse(changed.isError,str(changed));self.assertEqual(changed.structuredContent['preservation']['edited_texts'],1)
                    self.assertTrue(changed.structuredContent['preservation']['blocks_and_paper_entities_preserved'])
                    self.assertEqual(digest(root/'native/Drawing.dwg'),recipe['drawing_sha256'])


if __name__=='__main__':unittest.main()
