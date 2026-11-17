import importlib.util
import json
import os
from pathlib import Path
import sys
from datetime import timedelta
import unittest

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('mcp'),'Requires actual MCP SDK')
class SelectiveMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_mcp_checkpoint_impact_replay_and_delivery(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.test_changes import ChangeImpactTests
        fixture=ChangeImpactTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','bsa.mcp_server'],
            cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(fixture.root)})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools={t.name for t in (await session.list_tools()).tools}
                self.assertEqual(len(tools),42)
                self.assertTrue({'bsa_checkpoint_workflow','bsa_inspect_changes'}<=tools)
                async def call(name,args):
                    response=await session.call_tool(name,args,read_timeout_seconds=timedelta(seconds=120))
                    self.assertFalse(response.isError,str(response.content))
                    return response.structuredContent
                await call('bsa_execute_workflow',dict(plan='plan.json',out='mcp-baseline'))
                await call('bsa_checkpoint_workflow',dict(plan='plan.json',out='mcp-baseline',checkpoint='mcp-checkpoint'))
                fixture.change_primary()
                impact=await call('bsa_inspect_changes',dict(checkpoint='mcp-checkpoint',plan='plan.json'))
                self.assertTrue(impact['tasks']['analysis']['invalidated'])
                self.assertTrue(impact['tasks']['independent']['reuse_eligible'])
                await call('bsa_execute_workflow',dict(plan='plan.json',out='selective',reuse_checkpoint='mcp-checkpoint'))
                diagnosis=await call('bsa_diagnose_workflow',dict(plan='plan.json',out='selective'))
                self.assertTrue(diagnosis['integrity_pass'])
                artifacts=await call('bsa_artifact_index',dict(plan='plan.json',out='selective'))
                result=await call('bsa_read_artifact',dict(plan='plan.json',out='selective',artifact='independent/result.json',workflow_sha256=artifacts['workflow_sha256']))
                self.assertFalse(json.loads(result['content'])['design_accepted'])
                report=json.loads((fixture.root/'selective/workflow.json').read_text(encoding='utf-8'))
                self.assertEqual(report['reuse']['reused_tasks'],['independent'])
                review=await call('bsa_delivery_template',dict(plan='plan.json',out='selective',review='review.json'))
                self.assertEqual(len(review['requirements']),4)
                self.assertTrue(all(r['status']=='pending' for r in review['requirements']))
