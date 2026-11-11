import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.bim import run as author
from bsa.cli import digest
from bsa.modules import run as module
from bsa.module_water_rules import run,verify

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/circulation-ifc'


class ModuleWaterRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        author(EX/'model.json',cls.root/'native');ifc=cls.root/'native/model.ifc'
        sources={k:dict(path=os.path.relpath(p,cls.root),sha256=digest(p)) for k,p in [('project',EX/'project.json'),('binding',EX/'binding.json'),('ifc',ifc)]}
        request=dict(schema='bsa.module-request/1',project_id='rule-test',scenario_id='synthetic',capability='analysis.water.ifc-steady-graph',coordinate_frame=dict(id='synthetic',kind='source-world-si',length_unit='m',georeferenced=False),sources=sources)
        cls.request=cls.root/'request.json';cls.request.write_text(json.dumps(request));m=module(cls.request,'wntr.ifc-steady',cls.root/'module')
        assert m['payload']['status']=='pass';cls.producer=cls.root/'module/result.json'

    def setUp(self):
        self.folder=self.root/self._testMethodName;self.folder.mkdir();self.basis=self.folder/'basis.json';self.basis.write_bytes((EX/'regulatory-bases.json').read_bytes())
        # Contract/evaluator control only;actual official-file runs are retained separately.
        source=self.folder/'emsd-bec-2024.pdf';source.write_bytes(b'SYNTHETIC RULE TEST SOURCE')
        p=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text());p['sources']['emsd_bec_2024']['sha256']=digest(source)
        self.pack=self.folder/'pack.json';self.pack.write_text(json.dumps(p))

    def check(self,name):return run(self.producer,self.basis,self.pack,self.folder,self.folder/name)

    def test_positive_known_control_failure_and_unknown_are_distinct(self):
        r=self.check('positive');self.assertEqual(r['status'],'pass');verify(self.folder/'positive')
        self.assertEqual(r['assessment']['schema'],'bsa.rule-assessment/1')
        self.assertEqual(r['assessment']['status'],'pass')
        self.assertEqual({x['entity_id'] for x in r['assessment']['checks']},set(r['segment_checks']))
        for row in r['assessment']['coverage']:
            self.assertEqual(row['pending'],r['segment_checks'][row['entity_id']]['coverage']['pending'])
        self.assertEqual(r['regulatory_compliance'],'not_established');self.assertFalse(r['design_accepted'])
        b=json.loads(self.basis.read_text());original=copy.deepcopy(b)
        for row in b['pipes'].values():row['water_pipe'].update(flow_mode=dict(value='variable',source='Synthetic negative control'),pump_control=dict(value='single_fixed_speed',source='Synthetic negative control'))
        self.basis.write_text(json.dumps(b));self.assertEqual(self.check('control-fail')['status'],'fail');verify(self.folder/'control-fail')
        original['pipes']['OUTBOUND']['facts']['bec_air_conditioning_scope_confirmed']['value']=None
        self.basis.write_text(json.dumps(original));self.assertEqual(self.check('unknown')['status'],'pending');verify(self.folder/'unknown')

    def test_missing_official_source_and_later_availability_change_reject(self):
        source=self.folder/'emsd-bec-2024.pdf';data=source.read_bytes();source.unlink()
        self.assertEqual(self.check('missing')['status'],'pending');verify(self.folder/'missing')
        source.write_bytes(data)
        with self.assertRaisesRegex(ValueError,'inventory differs|availability changed'):verify(self.folder/'missing')

    def test_overrides_and_coherent_bound_fact_forgery_reject(self):
        b=json.loads(self.basis.read_text());original=copy.deepcopy(b);b['pipes']['OUTBOUND']['water_pipe']['velocity']=dict(value=0,unit='m/s',source='forged')
        self.basis.write_text(json.dumps(b))
        with self.assertRaisesRegex(ValueError,'cannot be overridden'):self.check('override')
        self.basis.write_text(json.dumps(original));self.check('good')
        folder=self.folder/'good';bound=folder/'bound-pipe-projects.json';p=json.loads(bound.read_text());p['OUTBOUND']['water_pipe']['velocity']['value']=0;bound.write_text(json.dumps(p))
        path=folder/'module-water-rules.json';r=json.loads(path.read_text());r['artifacts']['bound-pipe-projects.json']=digest(bound);path.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'bound facts differ'):verify(folder)

    def test_common_assessment_identity_and_forgery_reject(self):
        from bsa.module_contract import validate
        r=self.check('typed');a=copy.deepcopy(r['assessment'])
        a['checks'].append(copy.deepcopy(a['checks'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate(a)
        a=copy.deepcopy(r['assessment']);a['status']='fail'
        with self.assertRaisesRegex(ValueError,'contradicts'):validate(a)
        a=copy.deepcopy(r['assessment']);a['checks'][0]['original_status']='unknown_future_state'
        with self.assertRaisesRegex(ValueError,'original check meaning'):validate(a)
        a=copy.deepcopy(r['assessment']);a['coverage'].pop()
        with self.assertRaisesRegex(ValueError,'coverage must match'):validate(a)
        a=copy.deepcopy(r['assessment']);a['coverage'][0]['pending']=[]
        with self.assertRaisesRegex(ValueError,'Contract violation'):validate(a)
        path=self.folder/'typed/module-water-rules.json'
        r['assessment']['checks'][0]['entity_id']='OTHER-SYSTEM'
        path.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'assessment differs'):verify(path.parent)

    def test_unavailable_upstream_cannot_create_rule_assessment(self):
        module(self.request,'wntr.ifc-steady',self.folder/'disabled',disabled=True)
        with self.assertRaisesRegex(ValueError,'Passing verified'):run(self.folder/'disabled/result.json',self.basis,self.pack,self.folder,self.folder/'rejected')
        self.assertFalse((self.folder/'rejected').exists())

    def test_independent_domestic_water_project_cannot_use_hvac_pack(self):
        source=ROOT/'examples/water-loop-ifc'
        author(source/'model.json',self.folder/'domestic-native')
        upstream=json.loads(self.request.read_text());upstream['project_id']='independent-domestic-ring'
        upstream['sources']={k:dict(path=os.path.relpath(p,self.folder),sha256=digest(p)) for k,p in
            [('project',source/'project.json'),('binding',source/'binding.json'),('ifc',self.folder/'domestic-native/model.ifc')]}
        request=self.folder/'domestic-request.json';request.write_text(json.dumps(upstream))
        result=module(request,'wntr.ifc-steady',self.folder/'domestic-module')
        self.assertEqual(result['payload']['status'],'pass')
        with self.assertRaisesRegex(ValueError,'domestic water;HVAC water rule scope conflicts'):
            run(self.folder/'domestic-module/result.json',self.basis,self.pack,self.folder,self.folder/'wrong-rules')
        self.assertFalse((self.folder/'wrong-rules').exists())

    def test_registered_rule_provider_completion_disable_and_missing_cache(self):
        from bsa.modules import verify_result
        upstream=json.loads(self.producer.read_text())
        request=dict(schema='bsa.module-request/1',project_id=upstream['project_id'],scenario_id=upstream['scenario_id'],
            capability='regulation.water.saved-native',coordinate_frame=upstream['payload']['coordinate_frame'],
            sources={key:dict(path=os.path.relpath(path,self.folder),sha256=digest(path)) for key,path in
                [('producer',self.producer),('basis',self.basis),('pack',self.pack)]})
        path=self.folder/'rule-request.json';path.write_text(json.dumps(request))
        r=module(path,'bsa.hvac-water-rules',self.folder/'provider',runtime=dict(sources=self.folder))
        self.assertEqual(r['execution']['status'],'completed');self.assertEqual(r['payload']['status'],'pass')
        self.assertEqual(r['acceptance']['status'],'pending');verify_result(self.folder/'provider/result.json')
        for name,options in [('disabled',dict(disabled=True)),('missing-cache',{})]:
            result=module(path,'bsa.hvac-water-rules',self.folder/name,**options)
            self.assertEqual(result['execution']['status'],'unavailable');self.assertIsNone(result['payload'])
            verify_result(self.folder/name/'result.json')
        request['coordinate_frame']['id']='OTHER-FRAME';path2=self.folder/'changed-frame.json';path2.write_text(json.dumps(request))
        result=module(path2,'bsa.hvac-water-rules',self.folder/'frame-failure',runtime=dict(sources=self.folder))
        self.assertEqual(result['execution']['status'],'failed');self.assertIsNone(result['payload'])
        request['coordinate_frame']=upstream['payload']['coordinate_frame'];request['project_id']='OTHER-PROJECT'
        path3=self.folder/'changed-project.json';path3.write_text(json.dumps(request))
        result=module(path3,'bsa.hvac-water-rules',self.folder/'project-failure',runtime=dict(sources=self.folder))
        self.assertEqual(result['execution']['status'],'failed');self.assertIsNone(result['payload'])
