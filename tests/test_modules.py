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
