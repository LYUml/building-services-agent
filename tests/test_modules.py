import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.modules import ROOT,run,verify_result
from bsa.module_contract import validate,read_json


class ModuleContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.ifc=self.root/'source.ifc';self.ifc.write_text('Contract control fixture only;not native IFC')
        self.binding=self.root/'binding.json';self.binding.write_text('{}')
        self.request=dict(schema='bsa.module-request/1',project_id='fixture',scenario_id='baseline',capability='spatial.ifc-boxes.exchange',
            coordinate_frame=dict(id='fixture-world',kind='source-world-si',length_unit='m',georeferenced=False),
            sources={role:dict(path=p.name,sha256=digest(p)) for role,p in (('ifc',self.ifc),('binding',self.binding))})
        self.path=self.root/'request.json';self.save()

    def save(self):self.path.write_text(json.dumps(self.request))
    def execute(self,name='out',**kwargs):return run(self.path,'moosas.box-space-exchange',self.root/name,**kwargs)
    def payload(self):return dict(schema='bsa.spatial-boxes/1',coordinate_frame=self.request['coordinate_frame'],units=dict(length='m',area='m2'),classification='geometry-derived',spaces=[dict(id='A',origin_m=[0,0,0],size_m=[2,3,4],floor_area_m2=6)],contacts=[],simulation_ready=False)
    def fake(self,*args):return dict(status='completed',diagnostics=[],payload=self.payload(),pins={})

    def test_disabled_and_missing_runtime_never_claim_completed_geometry(self):
        with patch('bsa.providers.moosas_exchange.execute') as provider:r=self.execute(disabled=True)
        provider.assert_not_called();self.assertEqual(r['execution']['status'],'unavailable');self.assertIsNone(r['payload'])
        self.assertEqual(verify_result(self.root/'out/result.json'),r)
        missing=self.execute('missing');self.assertEqual(missing['execution']['diagnostics'][0]['code'],'runtime_missing')
        self.assertFalse(missing['design_accepted']);self.assertEqual(missing['acceptance']['status'],'pending')

    def test_native_provider_disabled_and_rejects_incompatible_capability(self):
        with patch('bsa.providers.ifc_boxes.execute') as provider:
            result=run(self.path,'ifcopenshell.box-spaces',self.root/'native-disabled',disabled=True)
        provider.assert_not_called()
        self.assertEqual(result['execution']['status'],'unavailable')
        self.assertEqual(verify_result(self.root/'native-disabled/result.json'),result)
        self.request['capability']='spatial.unsupported';self.save()
        with self.assertRaises(ValueError):run(self.path,'ifcopenshell.box-spaces',self.root/'bad-capability')
        self.assertFalse((self.root/'bad-capability').exists())

    def workflow_plan(self):
        brief=self.root/'brief.md';brief.write_text('Exchange the declared source spaces and retain engineering review.\n',encoding='utf-8')
        tasks=[dict(id='primary',kind='module_exchange',request='request.json',provider='moosas.box-space-exchange'),
            dict(id='dependent',kind='module_exchange',request='request.json',provider='ifcopenshell.box-spaces',requires_pass=['primary']),
            dict(id='independent',kind='module_exchange',request='request.json',provider='ifcopenshell.box-spaces')]
        plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions=dict(P001='requirement'),tasks=tasks,
            requirements=[dict(id='R'+str(i),task=t['id'],passage='P001',quote='Exchange the declared source spaces',acceptance='Review source geometry and engineering scope') for i,t in enumerate(tasks)])
        path=self.root/'plan.json';path.write_text(json.dumps(plan),encoding='utf-8');return path

    def test_workflow_disable_blocks_dependent_and_runs_independent(self):
        from bsa.workflow import execute,verify
        plan=self.workflow_plan()
        with patch('bsa.providers.moosas_exchange.execute') as disabled,patch('bsa.providers.ifc_boxes.execute',side_effect=self.fake) as native:
            result=execute(plan,self.root/'workflow',disabled_module_providers=['moosas.box-space-exchange'])
        disabled.assert_not_called();self.assertEqual(native.call_count,1)
        self.assertEqual([r['status'] for r in result['tasks'].values()],['pending','pending','pass'])
        self.assertFalse((self.root/'workflow/dependent').exists())
        self.assertTrue(verify(self.root/'workflow')['integrity_pass'])
        from bsa.workflow_status import diagnose
        diagnosis=diagnose(plan,self.root/'workflow')
        self.assertIn('enable the selected provider',diagnosis['actions'][0]['next_action'])
        self.assertEqual(diagnosis['actions'][0]['module_state']['execution']['diagnostics'][0]['code'],'provider_disabled')
        self.assertEqual(diagnosis['tasks'][1]['upstream_action_tasks'],['primary'])
        self.assertTrue(all(r['acceptance_status']=='pending review' for r in result['requirements']))
        (self.root/'workflow/independent/result.json').write_text('{}')
        self.assertFalse(verify(self.root/'workflow')['integrity_pass'])

    def test_workflow_provider_override_and_untrusted_runtime_fields(self):
        from bsa.workflow import execute,validate_plan
        plan=self.workflow_plan()
        with patch('bsa.providers.ifc_boxes.execute',side_effect=self.fake) as native:
            result=execute(plan,self.root/'replacement',module_providers=dict(primary='ifcopenshell.box-spaces'))
        self.assertEqual(native.call_count,3);self.assertTrue(result['execution_pass']);self.assertFalse(result['design_accepted'])
        with self.assertRaises(ValueError):execute(plan,self.root/'unknown',module_providers=dict(missing='ifcopenshell.box-spaces'))
        document=json.loads(plan.read_text());document['tasks'][0]['command']='untrusted';plan.write_text(json.dumps(document))
        with self.assertRaises(ValueError):validate_plan(plan)

    def test_workflow_thermal_inherits_and_simulation_waits_for_real_engine(self):
        from bsa.workflow import execute,verify,validate_plan
        plan=self.workflow_plan();data=json.loads(plan.read_text())
        (self.root/'thermal.json').write_bytes((ROOT/'examples/thermal-ifc/project.json').read_bytes())
        (self.root/'mapping.json').write_text(json.dumps(dict(source='Explicit synthetic test north and mapping',north_axis_deg=30,spaces=[dict(guid='A',id='ZoneA',source='Synthetic test identity')])) )
        (self.root/'weather.epw.gz').write_bytes((ROOT/'examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz').read_bytes())
        data['tasks']=[data['tasks'][0],dict(id='thermal',kind='module_thermal_project',depends_on='primary',project='thermal.json',binding='mapping.json'),dict(id='annual',kind='annual_energy',depends_on='thermal',weather='weather.epw.gz')]
        for row,task in zip(data['requirements'],data['tasks']):row['task']=task['id']
        plan.write_text(json.dumps(data))
        with patch('bsa.providers.moosas_exchange.execute',side_effect=self.fake):result=execute(plan,self.root/'thermal-run')
        self.assertEqual([r['status'] for r in result['tasks'].values()],['pass','pass','pending'])
        self.assertTrue(verify(self.root/'thermal-run')['integrity_pass'])
        bound=json.loads((self.root/'thermal-run/thermal/bound-project.json').read_text())
        self.assertEqual(bound['building']['spaces'][0]['size_m'],[2,3,4])
        self.assertFalse((self.root/'thermal-run/annual').exists())
        data['tasks'][2]['project']='thermal.json';plan.write_text(json.dumps(data))
        with self.assertRaises(ValueError):validate_plan(plan)

    def test_single_provider_override_survives_diagnosis_and_delivery_context(self):
        from bsa.workflow import execute
        from bsa.workflow_status import diagnose
        from bsa.delivery import template,context
        plan=self.workflow_plan();data=json.loads(plan.read_text());data['tasks']=data['tasks'][:1];data['requirements']=data['requirements'][:1];plan.write_text(json.dumps(data))
        folder=self.root/'single-override'
        with patch('bsa.providers.ifc_boxes.execute',side_effect=self.fake):
            result=execute(plan,folder,module_providers=dict(primary='ifcopenshell.box-spaces'))
        self.assertTrue(diagnose(plan,folder)['execution_pass'])
        review=template(plan,folder,self.root/'review.json')
        self.assertEqual(review['requirements'][0]['status'],'pending')
        result['module_selection']['providers']={};(folder/'workflow.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError,'differs from host selection'):context(plan,folder)

    def test_version_command_and_unknown_provider_reject_before_outputs(self):
        original=copy.deepcopy(self.request)
        for key,value in (('schema','bsa.module-request/2'),('command','echo untrusted'),('upstream','untrusted runtime')):
            self.request=copy.deepcopy(original);self.request[key]=value;self.save()
            with self.subTest(key=key),self.assertRaises(ValueError):self.execute()
            self.assertFalse((self.root/'out').exists())
        self.request=original;self.save()
        with self.assertRaises(ValueError):run(self.path,'document.import.path',self.root/'unknown')

    def test_changed_source_and_midrun_mutation_suppress_result(self):
        self.ifc.write_text('Changed input')
        with self.assertRaisesRegex(ValueError,'source missing or changed'):self.execute()
        self.assertFalse((self.root/'out').exists())
        self.request['sources']['ifc']['sha256']=digest(self.ifc);self.save()
        def mutate(*args):
            self.ifc.write_text('Changed during provider');return self.fake(*args)
        with patch('bsa.providers.moosas_exchange.execute',side_effect=mutate),self.assertRaisesRegex(ValueError,'changed during execution'):self.execute()
        self.assertFalse((self.root/'out/result.json').exists())

    def test_common_frame_and_invalid_provider_payload_are_failed_diagnostics(self):
        def wrong(*args):
            r=self.fake(*args);r['payload']['spaces'][0]['floor_area_m2']=99;return r
        with patch('bsa.providers.moosas_exchange.execute',side_effect=wrong):r=self.execute()
        self.assertEqual(r['execution']['status'],'failed');self.assertIsNone(r['payload']);self.assertEqual(r['execution']['diagnostics'][0]['code'],'payload_contract_invalid')
        def frame(*args):
            r=self.fake(*args);r['payload']['coordinate_frame']=dict(self.request['coordinate_frame'],id='wrong-world');return r
        with patch('bsa.providers.moosas_exchange.execute',side_effect=frame):r=self.execute('wrong-frame')
        self.assertEqual(r['execution']['status'],'failed');self.assertIsNone(r['payload'])

    def test_complete_inventory_artifact_mutation_and_missing_source_pins_reject(self):
        def artifact(*args):
            (args[-1]/'trace.txt').write_text('Fixture dispatch only;not an engine result');return self.fake(*args)
        # Mocked dispatch verifies contracts only;actual upstream calls are
        # executed separately and recorded as real provider evidence.
        with patch('bsa.providers.moosas_exchange.execute',side_effect=artifact):r=self.execute()
        self.assertEqual(verify_result(self.root/'out/result.json'),r)
        report=self.root/'out/result.json';bad=copy.deepcopy(r);bad['inputs'].pop(str(self.ifc));report.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'omitted a declared'):verify_result(report)
        bad=copy.deepcopy(r);bad['artifacts']={};report.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'inventory differs'):verify_result(report)
        report.write_text(json.dumps(r));(self.root/'out/trace.txt').write_text('Changed')
        with self.assertRaisesRegex(ValueError,'artifact evidence changed'):verify_result(report)

    def test_duplicate_nonfinite_unknown_units_and_false_acceptance_reject(self):
        self.path.write_text('{"schema":"a","schema":"b"}')
        with self.assertRaisesRegex(ValueError,'Duplicate'):read_json(self.path)
        self.path.write_text('{"value":NaN}')
        with self.assertRaisesRegex(ValueError,'Nonfinite'):read_json(self.path)
        data=self.payload();data['spaces'][0]['origin_m'][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'Nonfinite'):validate(data)
        data=self.payload();data['units']['length']='mm'
        with self.assertRaises(ValueError):validate(data)
        self.save();r=self.execute();r['acceptance']['status']='pass'
        with self.assertRaisesRegex(ValueError,'cannot pass acceptance'):validate(r)
