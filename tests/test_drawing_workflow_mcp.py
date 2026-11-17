import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import timedelta
import unittest
from bsa.native_cad import DEFAULT_EXE

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(importlib.util.find_spec('mcp') and DEFAULT_EXE.is_file(),'Requires MCP SDK and actual AutoCAD')
class DrawingWorkflowMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_workflow_diagnosis_and_separate_delivery_review(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);data=json.loads((ROOT/'examples/drawing-workflow-plan.json').read_text())
            data['brief']='brief.md';data['tasks'][0]['project']='document.json'
            (root/'plan.json').write_text(json.dumps(data))
            (root/'brief.md').write_bytes((ROOT/'examples/drawing-workflow/brief.md').read_bytes())
            (root/'document.json').write_bytes((ROOT/'examples/drawing-document.json').read_bytes())
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server','--autocad',str(DEFAULT_EXE)],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    response=await session.call_tool('bsa_execute_workflow',dict(plan='plan.json',out='execution'),read_timeout_seconds=timedelta(seconds=180))
                    self.assertFalse(response.isError,str(response));self.assertFalse(response.structuredContent['execution_pass'])
                    checked=await session.call_tool('bsa_diagnose_workflow',dict(plan='plan.json',out='execution'))
                    self.assertFalse(checked.isError,str(checked));self.assertTrue(checked.structuredContent['integrity_pass'])
                    tasks={t['id']:t for t in checked.structuredContent['tasks']}
                    self.assertEqual(tasks['sheet']['status'],'pass');self.assertEqual(tasks['review']['status'],'pending')
                    review=await session.call_tool('bsa_delivery_template',dict(plan='plan.json',out='execution',review='review.json'))
                    self.assertFalse(review.isError,str(review));self.assertEqual(len(review.structuredContent['requirements']),2)
                    self.assertTrue(all(r['status']=='pending' for r in review.structuredContent['requirements']))
                    self.assertTrue((root/'execution/sheet/Drawing.dwg').is_file())

if __name__=='__main__':unittest.main()
