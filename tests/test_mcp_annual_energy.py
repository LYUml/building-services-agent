import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from datetime import timedelta

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(importlib.util.find_spec('mcp') and os.environ.get('BSA_TEST_ENERGYPLUS'),'Requires explicit native EnergyPlus and MCP SDK')
class MCPAnnualEnergyTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_annual_logs_cannot_corrupt_workflow_response(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory)
            for name in ['brief.md','plan.json','project.json','USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz']:
                (root/name).write_bytes((ROOT/'examples/annual-energy'/name).read_bytes())
            params=StdioServerParameters(command=sys.executable,args=['-m','bsa.mcp_server','--energyplus',os.environ['BSA_TEST_ENERGYPLUS']],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    response=await session.call_tool('bsa_execute_workflow',dict(plan='plan.json',out='execution'),read_timeout_seconds=timedelta(seconds=180))
                    self.assertFalse(response.isError,str(response));self.assertTrue(response.structuredContent['execution_pass'])
                    self.assertFalse(response.structuredContent['design_accepted'])
                    result=json.loads((root/'execution/annual/annual.json').read_text())
                    self.assertTrue(result['calculated_checks_pass']);self.assertEqual(result['weather']['hours'],8760)
                    self.assertTrue((root/'execution/diagnosis.json').is_file())
                    review=await session.call_tool('bsa_delivery_template',dict(plan='plan.json',out='execution',review='review.json'))
                    self.assertFalse(review.isError,str(review));self.assertEqual(len(review.structuredContent['requirements']),1)
                    self.assertEqual(review.structuredContent['requirements'][0]['status'],'pending')

if __name__=='__main__':unittest.main()
