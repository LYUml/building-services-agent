import asyncio
import base64
from datetime import timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
FONT=Path('C:/Windows/Fonts/arial.ttf')

@unittest.skipUnless(importlib.util.find_spec('mcp') and FONT.is_file() and shutil.which('pdftoppm'),'requires MCP, host font and Poppler')
class MCPHVACProjectTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_client_prepares_runs_inspects_and_renders_package(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        from bsa.hvac_package_access import run
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);plan=runpy.run_path(str(ROOT/'examples/hvac-package/build_inputs.py'))['build'](root/'inputs')
            with self.assertRaisesRegex(ValueError,'Host report font'):run(root/'unneeded.json',root/'missing-font')
            self.assertFalse((root/'missing-font').exists())
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server','--report-font',str(FONT),'--pdftoppm',shutil.which('pdftoppm')],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    async def call(name,args):
                        result=await session.call_tool(name,args,read_timeout_seconds=timedelta(seconds=180))
                        self.assertFalse(result.isError,str(result));return result.structuredContent
                    prepared=await call('bsa_prepare_hvac_project',dict(plan='inputs/plan.json',out='project.json'))
                    self.assertFalse(prepared['design_accepted'])
                    result=await call('bsa_run_hvac_project',dict(configuration='project.json',out='package'))
                    self.assertTrue(result['integrity_pass']);self.assertFalse(result['design_accepted'])
                    self.assertEqual(result['stage_errors'],{});self.assertTrue(result['unresolved_tasks'])
                    inspected=await call('bsa_inspect_hvac_project',dict(configuration='project.json',out='package'))
                    self.assertEqual(result,inspected)
                    report=next(a for a in result['artifacts'] if a['path']=='report-pdf/HVAC System Design.pdf')
                    rendered=await session.call_tool('bsa_render_source_page',dict(source='package/'+report['path'],page=1,out='report-page'))
                    self.assertFalse(rendered.isError,str(rendered));self.assertEqual(rendered.structuredContent['source_sha256'],report['sha256'])
                    image=next(c for c in rendered.content if c.type=='image');self.assertEqual(hashlib.sha256(base64.b64decode(image.data)).hexdigest(),rendered.structuredContent['image_sha256'])
                    for name,args in [('bsa_run_hvac_project',dict(configuration='project.json',out='package')),('bsa_prepare_hvac_project',dict(plan='inputs/plan.json',out='../escape.json')),('bsa_run_hvac_project',dict(configuration='project.json',out='override',font=str(FONT)))]:
                        denied=await session.call_tool(name,args);self.assertTrue(denied.isError)
                    self.assertFalse((root/'override').exists())
                    path=root/'package'/report['path'];original=path.read_bytes();path.write_bytes(original+b'changed')
                    denied=await session.call_tool('bsa_inspect_hvac_project',dict(configuration='project.json',out='package'));self.assertTrue(denied.isError)
                    path.write_bytes(original)
                    source=root/'inputs/brief.md';source.write_bytes(source.read_bytes()+b'changed')
                    denied=await session.call_tool('bsa_inspect_hvac_project',dict(configuration='project.json',out='package'));self.assertTrue(denied.isError)

if __name__=='__main__':unittest.main()
