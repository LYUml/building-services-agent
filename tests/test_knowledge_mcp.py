"""Exercise the existing real MCP SDK routes, not direct tool-function mocks."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from datetime import timedelta
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Requires actual MCP SDK')
class KnowledgeMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_tools_build_query_read_and_keep_review_pending(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.test_knowledge_workflow import KnowledgeWorkflowTests
        fixture=KnowledgeWorkflowTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        params=StdioServerParameters(command=sys.executable,
            args=['-X','utf8','-m','bsa.mcp_server'],cwd=str(ROOT),
            env={**os.environ,'BSA_PROJECT_ROOT':str(fixture.root)})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                self.assertEqual(len((await session.list_tools()).tools),42)
                async def call(name,args):
                    response=await session.call_tool(name,args,read_timeout_seconds=timedelta(seconds=120))
                    self.assertFalse(response.isError,str(response.content))
                    return response.structuredContent
                result=await call('bsa_execute_workflow',dict(plan='plan.json',out='executed'))
                self.assertFalse(result['execution_pass'])
                diagnosis=await call('bsa_diagnose_workflow',dict(plan='plan.json',out='executed'))
                self.assertTrue(diagnosis['integrity_pass'])
                self.assertEqual({r['id']:r['status'] for r in diagnosis['tasks']},
                    dict(library='pass',lookup='pass',review='pending'))
                artifacts=await call('bsa_artifact_index',dict(plan='plan.json',out='executed'))
                args=dict(plan='plan.json',out='executed',artifact='lookup/query.json',
                    workflow_sha256=artifacts['workflow_sha256'])
                result=await call('bsa_read_artifact',args)
                query=json.loads(result['content'])
                self.assertEqual(len(query['hits']),1)
                self.assertTrue(query['matching_is_not_applicability'])
                review=await call('bsa_delivery_template',dict(plan='plan.json',out='executed',review='review.json'))
                self.assertEqual(len(review['requirements']),3)
                self.assertTrue(all(r['status']=='pending' for r in review['requirements']))
                fixture.source.write_text('Source changed after retrieval',encoding='utf-8')
                denied=await session.call_tool('bsa_read_artifact',args,read_timeout_seconds=timedelta(seconds=120))
                self.assertTrue(denied.isError)
