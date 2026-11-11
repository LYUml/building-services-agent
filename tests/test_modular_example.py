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
        for name in ('modular-plan.json','modular/brief.md','modular/request.json','thermal-ifc/bim.json','thermal-ifc/project.json','thermal-ifc/binding.json','annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz'):
            destination=self.root/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes((ROOT/'examples'/name).read_bytes())
        self.plan=self.root/'modular-plan.json'

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
