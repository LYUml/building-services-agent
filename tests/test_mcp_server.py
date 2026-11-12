import asyncio
import base64
import hashlib
import contextlib
import copy
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
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
            shutil.copyfile(ROOT/'docs/evidence/document-intake/source.pdf',root/'source.pdf')
            records=[];rejections=[];references=[]
            renderer=shutil.which('pdftoppm');preview=None;transcription=None
            params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','bsa.mcp_server',*(['--pdftoppm',renderer] if renderer else [])],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root),'PYTHONUTF8':'1'})
            with (root/'server.log').open('w',encoding='utf-8') as errors:
                async with stdio_client(params,errlog=errors) as (read,write):
                    async with ClientSession(read,write) as session:
                        initialized=(await session.initialize()).model_dump(mode='json')
                        tools=(await session.list_tools()).tools
                        self.assertEqual(len(tools),14)
                        for tool in tools:
                            self.assertFalse({'autocad','command','project_root'} & set(tool.inputSchema.get('properties',{})))
                        async def call(name,args):
                            result=await session.call_tool(name,args)
                            self.assertFalse(result.isError,str(result.content))
                            records.append(dict(tool=name,arguments=args,result=result.model_dump(mode='json')))
                            return result.structuredContent
                        graphical=await call('bsa_project_start',dict(brief='source.pdf',out='graphic-intake'))
                        self.assertEqual(graphical['status'],'needs_source_review')
                        before_review=(root/'graphic-intake/intake.json').read_bytes()
                        page=await session.call_tool('bsa_render_source_page',dict(source='source.pdf',page=1,out='source-page'))
                        if renderer:
                            self.assertFalse(page.isError,str(page.content));meta=page.structuredContent
                            image=next(c for c in page.content if c.type=='image')
                            self.assertEqual(hashlib.sha256(base64.b64decode(image.data)).hexdigest(),meta['image_sha256'])
                            self.assertEqual(base64.b64decode(image.data),(root/'source-page/page.png').read_bytes())
                            self.assertFalse(meta['extraction_review_cleared']);self.assertFalse(meta['design_accepted'])
                            self.assertEqual((root/'graphic-intake/intake.json').read_bytes(),before_review)
                            preview=dict(metadata=meta,base64_matches_saved_png=True,extraction_review_unchanged=True)
                            records.append(dict(tool='bsa_render_source_page',arguments=dict(source='source.pdf',page=1,out='source-page'),result=page.model_dump(mode='json')))
                            for bad in [dict(page=2),dict(page=True),dict(page=1,max_side=3000)]:
                                invalid=await session.call_tool('bsa_render_source_page',dict(source='source.pdf',out='invalid-page',**bad))
                                self.assertTrue(invalid.isError);self.assertFalse((root/'invalid-page').exists())
                            pages=[dict(page=1,receipt='source-page/page.json',lines=[dict(text=f'L{i} / LGT-1',box=[[x,660],[x+410,660],[x+410,760],[x,760]]) for i,x in [(1,240),(2,850),(3,1480)]])]
                            prepared=await call('bsa_prepare_visual_transcription',dict(source='source.pdf',pages=pages,sidecar='visual-transcription.json',target='visual-plan.json'))
                            self.assertEqual(prepared['status'],'needs_source_review')
                            visual=await call('bsa_read_source_plan',dict(plan='visual-plan.json'))
                            self.assertEqual([r['text'] for r in visual['documents']['passages']],['L1 / LGT-1','L2 / LGT-1','L3 / LGT-1'])
                            self.assertTrue(all(r['transcription_method']=='host_visual_transcription' and 'confidence' not in r for r in visual['documents']['passages']))
                            blocked_template=await session.call_tool('bsa_handoff_template',dict(plan='visual-plan.json',out='blocked-visual-template.json'))
                            self.assertTrue(blocked_template.isError);self.assertFalse((root/'blocked-visual-template.json').exists())
                            notes={issue['id']:'Actual rendered public page inspected: literal labels checked; no supplied physical dimensions and none inferred. Source graphical completeness and transcription inspected; engineering meaning remains pending.' for issue in visual['documents']['issues']}
                            reviewed=await call('bsa_review_source_plan',dict(plan='visual-plan.json',notes=notes,out='visual-reviewed-plan.json'))
                            self.assertEqual(reviewed['status'],'needs_interpretation')
                            next_plan=await call('bsa_read_source_plan',dict(plan='visual-reviewed-plan.json'))
                            for key in ('tasks','requirements','unresolved_inputs'):self.assertEqual(next_plan['plan'][key],visual['plan'][key])
                            template=await call('bsa_handoff_template',dict(plan='visual-reviewed-plan.json',out='visual-template.json'))
                            self.assertFalse(template['executable']);self.assertEqual(template['original_requirements'],3)
                            transcription=dict(prepared=prepared,reviewed=reviewed,template=template,source_meaning='not_assessed',ordinary_gaps_preserved=True)
                        else:
                            self.assertTrue(page.isError);self.assertFalse((root/'source-page').exists())
                        intake=await call('bsa_project_start',dict(brief='brief.md',out='project'))
                        self.assertEqual(intake['status'],'needs_interpretation')
                        source=await call('bsa_read_source_plan',dict(plan='project/plan.json'))
                        self.assertEqual(len(source['plan']['requirements']),5)
                        await call('bsa_handoff_template',dict(plan='project/plan.json',out='project/template.json'))
                        blank=await session.call_tool('bsa_execute_handoff',dict(plan='project/plan.json',interpretation='project/template.json',target='project/blank-plan.json',out='blank-run'))
                        self.assertTrue(blank.isError);self.assertFalse((root/'blank-run').exists())
                        input_references={'electrical.json':'examples/office-electrical/project.json','air.json':'examples/network-design/project.json',
                            'air-catalogue.json':'examples/network-design/catalogue.json','water.json':'examples/network/water.json','envelopes.json':'examples/mep-ifc/project.json'}
                        for target,name in input_references.items():
                            index=await call('bsa_reference_catalogue',dict(kind='example',query=name))
                            row=next(row for row in index['references'] if row['path']==name)
                            resource=await session.read_resource(row['uri']);data=json.loads(resource.contents[0].text)
                            self.assertEqual(hashlib.sha256(data['content_utf8'].encode('utf-8')).hexdigest(),data['sha256'])
                            self.assertEqual(data['revision'],index['revision']);self.assertFalse(data['design_accepted'])
                            references.append({k:v for k,v in data.items() if k!='content_utf8'})
                            await call('bsa_save_json',dict(path='project/'+target,data=json.loads(data['content_utf8'])))
                        plan=source['plan']
                        tasks=[dict(id='electrical',kind='electrical',project='electrical.json'),dict(id='air',kind='network_design',project='air.json',catalogue='air-catalogue.json'),
                            dict(id='water',kind='network',project='water.json'),dict(id='envelopes',kind='bim',project='envelopes.json'),
                            dict(id='review',kind='manual',requires_pass=['electrical','air','water','envelopes'],description='Review complete original source obligations, physical applicability, products, native drawing and regulatory gaps.')]
                        review=dict(schema='bsa.engineering-handoff/1',source_plan_sha256=source['plan_sha256'],tasks=tasks,
                            requirement_bindings={r['id']:dict(tasks=[t['id']],acceptance=r['quote']) for r,t in zip(plan['requirements'],tasks)},
                            interpretation_notes={i['id']:'Authored public synthetic interpretation; full source quote mapped to existing adapter and declared synthetic references '+json.dumps(references)+'; not semantic generalisation.' for i in plan['unresolved_inputs']},extra_unresolved_inputs=[])
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
                        source_guide=await session.read_resource('bsa://source-guide')
                        self.assertIn('bsa.visual-transcription/1',source_guide.contents[0].text)
                        reference_guide=await session.read_resource('bsa://reference-guide')
                        self.assertIn('bsa_reference_catalogue',reference_guide.contents[0].text)
                        recovery_guide=await session.read_resource('bsa://recovery-guide')
                        self.assertIn('bsa_recover_pump_catalogue',recovery_guide.contents[0].text)
                        skill=await session.read_resource('bsa://skills/building-services-design')
                        self.assertIn('building-services-design',skill.contents[0].text)
                        outside=await session.call_tool('bsa_read_source_plan',dict(plan=str(root/'project/plan.json')))
                        self.assertTrue(outside.isError)
            (root/'protocol.json').write_text(json.dumps(dict(sdk_version=importlib.metadata.version('mcp'),initialize=initialized,
                tools=[tool.model_dump(mode='json') for tool in tools],calls=records,rejected_paths=rejections,
                blank_interpretation_rejected=blank.isError,absolute_path_rejected=outside.isError,
                page_preview=preview,visual_transcription=transcription,references=references,engineering_verification=checked,uninterpreted_execution_pass=blocked['execution_pass'],design_accepted=False),indent=2),encoding='utf-8')


    async def test_real_pump_catalogue_recovery_uses_original_electrical_and_preserves_failure(self):
        persistent=os.environ.get('BSA_MCP_RECOVERY_TRIAL_OUT')
        if persistent:
            output=Path(persistent).resolve()
            if not output.is_relative_to(ROOT/'runs') or output.exists():raise ValueError('Fresh repository runs recovery trial required')
            output.mkdir(parents=True);directory=contextlib.nullcontext(str(output))
        else:directory=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        with directory as folder:
            root=Path(folder);(root/'coupled').mkdir()
            shutil.copyfile(ROOT/'examples/water-riser/coupled-brief.md',root/'coupled/coupled-brief.md')
            records=[];references=[]
            params=StdioServerParameters(command=sys.executable,args=['-X','utf8','-m','bsa.mcp_server'],cwd=str(ROOT),env={**os.environ,'BSA_PROJECT_ROOT':str(root),'PYTHONUTF8':'1'})
            with (root/'server.log').open('w',encoding='utf-8') as errors:
                async with stdio_client(params,errlog=errors) as (read,write):
                    async with ClientSession(read,write) as session:
                        await session.initialize()
                        async def call(name,args):
                            result=await session.call_tool(name,args);self.assertFalse(result.isError,str(result.content))
                            records.append(dict(tool=name,arguments=args,result=result.model_dump(mode='json')))
                            return result.structuredContent
                        good=None;plan_spec=None
                        for name in ['electrical.json','model.json','network.json','binding.json','catalogue.json','geometry.json','policy.json','drawing-settings.json','pump-electrical-link.json','pump-curve.json','coupled-plan.json']:
                            path='examples/water-riser/'+name;index=await call('bsa_reference_catalogue',dict(kind='example',query=path))
                            row=next(r for r in index['references'] if r['path']==path)
                            resource=await session.read_resource(row['uri']);ref=json.loads(resource.contents[0].text)
                            self.assertEqual(hashlib.sha256(ref['content_utf8'].encode('utf-8')).hexdigest(),ref['sha256'])
                            references.append({k:v for k,v in ref.items() if k!='content_utf8'})
                            data=json.loads(ref['content_utf8'])
                            if name=='coupled-plan.json':plan_spec=data
                            if name=='pump-curve.json':
                                good=copy.deepcopy(data)
                                await call('bsa_save_json',dict(path='coupled/source-pump-curve.json',data=good))
                                for point in data['points']:point['total_pressure_rise_pa']*=.65
                                data['sources'][data['source']]+=' Explicit synthetic insufficient-pressure baseline control: pressures scaled by0.65; not actual equipment.'
                            await call('bsa_save_json',dict(path='coupled/'+name,data=data))
                        self.assertIsNotNone(good)
                        bad=copy.deepcopy(good)
                        for point in bad['points']:point['wire_to_water_efficiency']=.02 if point['flow_m3_s'] else 0
                        bad['sources'][bad['source']]+=' Explicit synthetic low-efficiency adverse electrical control; not manufacturer data.'
                        rows=[dict(id='preferred-low-efficiency',source='Synthetic adverse electrical input',preference=0,curve=bad),dict(id='eligible',source='Original synthetic source curve',preference=1,curve=good)]
                        catalogue=dict(objective='lowest declared preference among passing candidates',source='Declared synthetic supplied curves; no real product approval',candidates=rows)
                        await call('bsa_save_json',dict(path='coupled/pump-catalogue.json',data=catalogue))
                        original=await call('bsa_execute_workflow',dict(plan='coupled/coupled-plan.json',out='coupled/original-run'))
                        self.assertFalse(original['execution_pass'])
                        ready=original['recovery_schedule']['ready_tasks']
                        recoverable=[t['id'] for t in plan_spec['tasks'] if t['id'] in ready and t['kind']=='pump_operating_point']
                        self.assertEqual(recoverable,['pump']);pump_task=recoverable[0]
                        before=(root/'coupled/coupled-plan.json').read_bytes();failure=(root/'coupled/original-run/workflow.json').read_bytes()
                        recovered=await call('bsa_recover_pump_catalogue',dict(plan='coupled/coupled-plan.json',original_run='coupled/original-run',task=pump_task,catalogue='coupled/pump-catalogue.json',target='coupled/selected-plan.json',out='coupled/selection',electrical_task='coupled'))
                        self.assertEqual(recovered['screening']['selected']['id'],'eligible')
                        rejected=recovered['screening']['candidates'][0]
                        self.assertTrue(rejected['numerical_checks_pass']);self.assertEqual(rejected['electrical']['status'],'fail')
                        checked=await call('bsa_verify_pump_recovery',dict(out='coupled/selection'))
                        self.assertTrue(checked['integrity_pass']);self.assertTrue(checked['full_plan_executed']);self.assertFalse(checked['design_accepted'])
                        diagnosis=await call('bsa_diagnose_workflow',dict(plan='coupled/selected-plan.json',out='coupled/selection/replay/workflow'))
                        self.assertTrue(all(t['status']=='pass' for t in diagnosis['tasks']))
                        catalogue['candidates']=rows[:1]
                        await call('bsa_save_json',dict(path='coupled/no-eligible-catalogue.json',data=catalogue))
                        stopped=await call('bsa_recover_pump_catalogue',dict(plan='coupled/coupled-plan.json',original_run='coupled/original-run',task=pump_task,catalogue='coupled/no-eligible-catalogue.json',target='coupled/no-selected-plan.json',out='coupled/selection-none',electrical_task='coupled'))
                        self.assertEqual(stopped['status'],'no_feasible_candidate')
                        negative=await call('bsa_verify_pump_recovery',dict(out='coupled/selection-none'))
                        self.assertTrue(negative['integrity_pass']);self.assertFalse(negative['full_plan_executed'])
                        self.assertFalse((root/'coupled/no-selected-plan.json').exists());self.assertFalse((root/'coupled/selection-none/replay').exists())
                        self.assertEqual(before,(root/'coupled/coupled-plan.json').read_bytes());self.assertEqual(failure,(root/'coupled/original-run/workflow.json').read_bytes())
            (root/'protocol.json').write_text(json.dumps(dict(calls=records,references=references,positive=checked,negative=negative,diagnosis=diagnosis,
                original_plan_and_failed_run_preserved=True,design_accepted=False),indent=2),encoding='utf-8')


class MCPWorkerTests(unittest.TestCase):
    def test_unknown_worker_operation_cannot_become_a_command(self):
        result=subprocess.run([sys.executable,'-X','utf8','-m','bsa.mcp_worker'],input=json.dumps(dict(operation='os.system',args=['untrusted document command'],kwargs={})),text=True,encoding='utf-8',capture_output=True,cwd=ROOT)
        self.assertEqual(result.returncode,2)
        self.assertFalse(json.loads(result.stdout)['ok'])


if __name__=='__main__':unittest.main()
