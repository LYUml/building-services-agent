"""Actual SDK workflow/data access; native CAD acceptance is a separate gate."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from datetime import timedelta
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Requires actual MCP SDK')
class CommonDataMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_tools_execute_diagnose_and_read_common_data(self):
        await self.execute_common_data(False)

    async def test_existing_tools_also_read_source_inputs_without_promoting_assertions(self):
        await self.execute_common_data(True)

    async def execute_common_data(self, include_inputs):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.test_engineering_data_workflow import CommonDataWorkflowTests
        fixture = CommonDataWorkflowTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root = fixture.root
        if include_inputs:
            fixture.plan_data['tasks'][1]['include_inputs'] = True
            fixture.save(fixture.plan, fixture.plan_data)
        params = StdioServerParameters(command=sys.executable,
            args=['-X', 'utf8', '-m', 'bsa.mcp_server'], cwd=str(ROOT),
            env={**os.environ, 'BSA_PROJECT_ROOT': str(root)})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                self.assertEqual(len((await session.list_tools()).tools), 44)

                async def call(name, arguments):
                    response = await session.call_tool(name, arguments,
                        read_timeout_seconds=timedelta(seconds=120))
                    self.assertFalse(response.isError, str(response.content))
                    return response.structuredContent

                result = await call('bsa_execute_workflow', dict(plan='plan.json', out='executed'))
                self.assertFalse(result['execution_pass'])
                diagnosed = await call('bsa_diagnose_workflow', dict(plan='plan.json', out='executed'))
                self.assertTrue(diagnosed['integrity_pass'])
                states = {r['id']: r['status'] for r in diagnosed['tasks']}
                self.assertEqual(states, dict(analysis='pass', data='pass', review='pending'))
                index = await call('bsa_artifact_index', dict(plan='plan.json', out='executed'))
                artifact = await call('bsa_read_artifact', dict(plan='plan.json', out='executed',
                    artifact='data/model.json', workflow_sha256=index['workflow_sha256']))
                model = json.loads(artifact['content'])
                self.assertEqual(model['project_id'], fixture.context['project_id'])
                self.assertEqual(model['schema'], 'bsa.engineering-data/1')
                self.assertFalse(model['design_accepted'])
                if include_inputs:
                    item = await call('bsa_read_artifact', dict(plan='plan.json', out='executed',
                        artifact='data/inputs.json', workflow_sha256=index['workflow_sha256']))
                    inputs = json.loads(item['content'])
                    self.assertEqual(len(inputs['parameters']), 20)
                    self.assertFalse(inputs['source_assertions_authenticated'])
                    self.assertTrue(all(r['quantity']['classification']=='declared' for r in inputs['parameters']))
                review = await call('bsa_delivery_template', dict(plan='plan.json', out='executed', review='review.json'))
                self.assertEqual(len(review['requirements']), 3)
                self.assertTrue(all(r['status'] == 'pending' for r in review['requirements']))
