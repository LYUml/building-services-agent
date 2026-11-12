import asyncio
import contextlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import subprocess
import tempfile
import unittest

if importlib.util.find_spec('mcp'):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('mcp'),'requires optional pinned MCP SDK')
class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_source_to_engineering_and_workspace_controls(self):
        persistent=os.environ.get('BSA_MCP_TRIAL_OUT')
        if persistent:
            output=Path(persistent).resolve()
            if not output.is_relative_to(ROOT/'runs') or output.exists():raise ValueError('Fresh repository runs trial directory required')
            output.mkdir(parents=True);directory=contextlib.nullcontext(str(output))
        else:directory=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        with directory as folder:
            root=Path(folder);shutil.copyfile(ROOT/'examples/engineering-handoff/brief.md',root/'brief.md')
            records=[];rejections=[]
            params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','bsa.mcp_server'],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root),'PYTHONUTF8':'1'})
            with (root/'server.log').open('w',encoding='utf-8') as errors:
                async with stdio_client(params,errlog=errors) as (read,write):
                    async with ClientSession(read,write) as session:
                        initialized=(await session.initialize()).model_dump(mode='json')
                        tools=(await session.list_tools()).tools
                        self.assertEqual(len(tools),8)
                        for tool in tools:
                            self.assertFalse({'autocad','command','project_root'} & set(tool.inputSchema.get('properties',{})))
                        async def call(name,args):
                            result=await session.call_tool(name,args)
                            self.assertFalse(result.isError,str(result.content))
                            records.append(dict(tool=name,arguments=args,result=result.model_dump(mode='json')))
                            return result.structuredContent
                        intake=await call('bsa_project_start',dict(brief='brief.md',out='project'))
                        self.assertEqual(intake['status'],'needs_interpretation')
                        source=await call('bsa_read_source_plan',dict(plan='project/plan.json'))
                        self.assertEqual(len(source['plan']['requirements']),5)
                        await call('bsa_handoff_template',dict(plan='project/plan.json',out='project/template.json'))
                        blank=await session.call_tool('bsa_execute_handoff',dict(plan='project/plan.json',interpretation='project/template.json',target='project/blank-plan.json',out='blank-run'))
                        self.assertTrue(blank.isError);self.assertFalse((root/'blank-run').exists())
                        demo=runpy.run_path(str(ROOT/'scripts/run_engineering_handoff_demo.py'))
                        for target,name in demo['INPUTS'].items():
                            await call('bsa_save_json',dict(path='project/'+target,data=json.loads((ROOT/name).read_text())))
                        plan=source['plan'];tasks=demo['TASKS']
                        review=dict(schema='bsa.engineering-handoff/1',source_plan_sha256=source['plan_sha256'],tasks=tasks,
                            requirement_bindings={r['id']:dict(tasks=[t['id']],acceptance=r['quote']) for r,t in zip(plan['requirements'],tasks)},
                            interpretation_notes={i['id']:'Authored public synthetic interpretation; full source quote mapped to the existing adapter with declared synthetic data; not semantic generalisation.' for i in plan['unresolved_inputs']},extra_unresolved_inputs=[])
                        await call('bsa_save_json',dict(path='project/interpretation.json',data=review))
                        for path in ['../outside.json','project/interpretation.json','project/program.py']:
                            result=await session.call_tool('bsa_save_json',dict(path=path,data={}))
                            self.assertTrue(result.isError)
                            rejections.append(path)
                        result=await call('bsa_execute_handoff',dict(plan='project/plan.json',interpretation='project/interpretation.json',target='project/engineering-plan.json',out='engineering-run'))
                        self.assertEqual(result['stage_errors'],{});self.assertFalse(result['design_accepted'])
                        checked=await call('bsa_verify_handoff',dict(out='engineering-run'))
                        self.assertTrue(checked['integrity_pass'])
                        self.assertEqual(checked['task_statuses'],dict(electrical='pass',air='pass',water='pass',envelopes='pass',review='pending'))
                        diagnosis=await call('bsa_diagnose_workflow',dict(plan='project/engineering-plan.json',out='engineering-run/workflow'))
                        self.assertFalse(diagnosis['execution_pass'])
                        blocked=await call('bsa_execute_workflow',dict(plan='project/plan.json',out='uninterpreted-run'))
                        self.assertFalse(blocked['execution_pass']);self.assertFalse(blocked['design_accepted'])
                        resources=await session.list_resources()
                        self.assertIn('bsa://guide',[str(r.uri) for r in resources.resources])
                        skill=await session.read_resource('bsa://skills/building-services-design')
                        self.assertIn('building-services-design',skill.contents[0].text)
                        outside=await session.call_tool('bsa_read_source_plan',dict(plan=str(root/'project/plan.json')))
                        self.assertTrue(outside.isError)
            (root/'protocol.json').write_text(json.dumps(dict(sdk_version=importlib.metadata.version('mcp'),initialize=initialized,
                tools=[tool.model_dump(mode='json') for tool in tools],calls=records,rejected_paths=rejections,
                blank_interpretation_rejected=blank.isError,absolute_path_rejected=outside.isError,
                engineering_verification=checked,uninterpreted_execution_pass=blocked['execution_pass'],design_accepted=False),indent=2),encoding='utf-8')


class MCPWorkerTests(unittest.TestCase):
    def test_unknown_worker_operation_cannot_become_a_command(self):
        result=subprocess.run([sys.executable,'-X','utf8','-m','bsa.mcp_worker'],input=json.dumps(dict(operation='os.system',args=['untrusted document command'],kwargs={})),text=True,encoding='utf-8',capture_output=True,cwd=ROOT)
        self.assertEqual(result.returncode,2)
        self.assertFalse(json.loads(result.stdout)['ok'])


if __name__=='__main__':unittest.main()
