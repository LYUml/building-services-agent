import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.workflow import execute,validate_plan,verify
from bsa.workflow_status import diagnose
from bsa.delivery import template

ROOT=Path(__file__).resolve().parents[1]


class ModularExampleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('modular-plan.json','modular-authoring-plan.json','modular/authoring.json','modular/brief.md','modular/request.json','thermal-ifc/bim.json','thermal-ifc/project.json','thermal-ifc/binding.json','annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz'):
            destination=self.root/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes((ROOT/'examples'/name).read_bytes())
        self.plan=self.root/'modular-plan.json'

    def test_native_authoring_provider_to_spatial_and_thermal(self):
        plan=self.root/'modular-authoring-plan.json';out=self.root/'authoring';result=execute(plan,out)
        self.assertEqual([t['status'] for t in result['tasks'].values()],['pass','pass','pass','pending','pending'])
        self.assertTrue(verify(out)['integrity_pass']);self.assertTrue(diagnose(plan,out)['integrity_pass'])
        review=template(plan,out,self.root/'authoring-review.json');self.assertTrue(all(r['status']=='pending' for r in review['requirements']))
        payload=json.loads((out/'model/result.json').read_text())['payload']
        self.assertEqual(payload['model']['path'],'native/model.ifc')
        request=json.loads((out/'spaces/request.json').read_text())
        self.assertEqual((out/'spaces'/request['sources']['ifc']['path']).resolve(),out/'model/native/model.ifc')

    def test_disabled_authoring_does_not_launch_worker_or_dependents(self):
        with patch('bsa.providers.ifc_authoring.execute') as worker:
            result=execute(self.root/'modular-authoring-plan.json',self.root/'disabled-author',disabled_module_providers=['ifcopenshell.bim-authoring'])
        worker.assert_not_called();self.assertTrue(all(t['status']=='pending' for t in result['tasks'].values()))
        self.assertFalse((self.root/'disabled-author/spaces').exists())

    def test_authoring_frame_mismatch_blocks_spatial_materialization(self):
        path=self.root/'modular/request.json';data=json.loads(path.read_text());data['coordinate_frame']['id']='different-frame';path.write_text(json.dumps(data))
        result=execute(self.root/'modular-authoring-plan.json',self.root/'frame-mismatch')
        self.assertEqual(result['tasks']['model']['status'],'pass');self.assertEqual(result['tasks']['spaces']['status'],'fail')
        self.assertIn('source frames differ',result['tasks']['spaces']['scope'])
        self.assertFalse((self.root/'frame-mismatch/spaces').exists())

    def test_model_artifact_path_and_inventory_contract_reject_tampering(self):
        from bsa.module_contract import validate
        import copy
        frame=json.loads((self.root/'modular/request.json').read_text())['coordinate_frame']
        data=dict(schema='bsa.model-artifact/1',coordinate_frame=frame,length_unit='m',model=dict(path='native/model.ifc',sha256='0'*64,format='IFC4'),verification=dict(path='native/check.json',sha256='1'*64),geometry_scope='Synthetic contract fixture',checks=dict(reopened=True),design_accepted=False)
        validate(data)
        bad=copy.deepcopy(data);bad['model']['path']='../outside.ifc'
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(data);bad['checks']['reopened']=False
        with self.assertRaises(ValueError):validate(bad)
        from bsa.modules import run
        result=run(self.root/'modular/authoring.json','ifcopenshell.bim-authoring',self.root/'contract-disabled',disabled=True)
        result['execution']=dict(status='completed',diagnostics=[]);result['payload']=data
        with self.assertRaisesRegex(ValueError,'artifact inventory'):validate(result)

    def test_public_native_authoring_to_thermal_preparation_and_review(self):
        out=self.root/'run';result=execute(self.plan,out)
        self.assertEqual([t['status'] for t in result['tasks'].values()],['pass','pass','pass','pending','pending'])
        self.assertTrue(verify(out)['integrity_pass']);self.assertTrue(diagnose(self.plan,out)['integrity_pass'])
        review=template(self.plan,out,self.root/'review.json');self.assertTrue(all(r['status']=='pending' for r in review['requirements']))
        request=json.loads((out/'spaces/request.json').read_text())
        self.assertEqual((out/'spaces'/request['sources']['ifc']['path']).resolve(),out/'model/model.ifc')
        self.assertEqual(len(json.loads((out/'thermal/bound-project.json').read_text())['building']['spaces']),3)
        self.assertFalse((out/'annual').exists())

    def test_failed_authoring_blocks_inherited_module_without_materialization(self):
        with patch('bsa.bim.run',side_effect=ValueError('Controlled authoring failure;no native result')):
            result=execute(self.plan,self.root/'failed')
        self.assertEqual([t['status'] for t in result['tasks'].values()],['fail','pending','pending','pending','pending'])
        self.assertFalse((self.root/'failed/spaces').exists())

    def test_replacement_ifc_in_template_and_incompatible_producer_reject(self):
        request=self.root/'modular/request.json';data=json.loads(request.read_text());data['sources']['ifc']=data['sources']['binding'];request.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'replacement IFC forbidden'):validate_plan(self.plan)
        request.write_bytes((ROOT/'examples/modular/request.json').read_bytes())
        plan=json.loads(self.plan.read_text());plan['tasks'][1]['depends_on']='review';self.plan.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):validate_plan(self.plan)
