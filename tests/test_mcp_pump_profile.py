"""Actual pure pump MCP iteration; the CI profile excludes IFC and Manifold."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('mcp') and importlib.util.find_spec('fluids'),'Requires MCP/network profile')
class MCPPumpProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_recovery_keeps_baseline_and_manual_review(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples/pump-recovery',root,dirs_exist_ok=True)
            plan=(root/'plan.json').read_bytes()
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server'],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    async def call(name,args):
                        response=await session.call_tool(name,args)
                        self.assertFalse(response.isError,str(response.content))
                        return response.structuredContent
                    baseline=await call('bsa_execute_workflow',dict(plan='plan.json',out='baseline'))
                    self.assertFalse(baseline['execution_pass'])
                    before=hashlib.sha256((root/'baseline/workflow.json').read_bytes()).hexdigest()
                    result=await call('bsa_run_recovery',dict(plan='plan.json',original_run='baseline',policy='policy.json',out='recovery'))
                    checked=await call('bsa_verify_recovery',dict(out='recovery'))
                    self.assertTrue(checked['integrity_pass']);self.assertEqual(checked['steps'],1)
                    self.assertFalse(checked['execution_pass']);self.assertFalse(checked['design_accepted'])
                    final=Path(result['final_run']);self.assertTrue(final.is_relative_to(root))
                    report=json.loads((final/'workflow.json').read_text())
                    self.assertEqual({name:row['status'] for name,row in report['tasks'].items()},dict(pump='pass',review='pending'))
                    self.assertEqual(json.loads(Path(result['final_plan']).read_text())['requirements'],json.loads(plan)['requirements'])
                    self.assertEqual((root/'plan.json').read_bytes(),plan)
                    self.assertEqual(hashlib.sha256((root/'baseline/workflow.json').read_bytes()).hexdigest(),before)


if __name__=='__main__':unittest.main()
