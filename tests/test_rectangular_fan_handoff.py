import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.workflow import execute,verify,validate_plan
from bsa.rectangular_fan_selection import selected_input
from bsa.cli import digest
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'

class RectangularFanHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.result=execute(EX/'fan-selected-plan.json',cls.root/'run')
        cls.base=cls.root/'run/air';cls.selection=cls.root/'run/fan'

    def invoke(self,producer):
        return selected_input(producer,self.base/'network-input.json',EX/'elbow-chain-model.json',EX/'elbow-chain-binding.json',self.base/'bim/model.ifc',self.base/'analysis/network.json',EX/'fan-catalogue.json')

    def copy(self):
        folder=self.root/self._testMethodName;shutil.copytree(self.selection,folder);return folder

    def rewrite(self,folder,change):
        p=folder/'fan-selection.json';r=json.loads(p.read_text());change(r);p.write_text(json.dumps(r))

    def test_actual_selected_consumer_and_integrity(self):
        self.assertEqual(self.result['tasks']['selected-operation']['status'],'pass')
        self.assertEqual(self.invoke(self.selection),self.selection/'selected/curve.json')
        self.assertTrue(verify(self.root/'run')['integrity_pass'])
        consumer=json.loads((self.root/'run/selected-operation/fan.json').read_text())
        self.assertTrue(consumer['geometry_bound']);self.assertTrue(consumer['selected_rerun_pass'])

    def test_curve_tamper_even_rehashed_rejects(self):
        folder=self.copy();path=folder/'selected/curve.json';c=json.loads(path.read_text());c['speed_rpm']=1400;path.write_text(json.dumps(c))
        self.rewrite(folder,lambda r:r['artifacts'].__setitem__('selected/curve.json',digest(path)))
        with self.assertRaisesRegex(ProjectError,'sourced reconstruction'):self.invoke(folder)

    def test_forged_candidate_success_rejected(self):
        folder=self.copy()
        self.rewrite(folder,lambda r:r['candidates'][0].update(status='converged',calculated_checks_pass=True))
        with self.assertRaisesRegex(ProjectError,'fresh fan solve'):self.invoke(folder)

    def test_wrong_selected_identity_rejected(self):
        folder=self.copy();self.rewrite(folder,lambda r:r['selected'].update(id='weak'))
        with self.assertRaisesRegex(ProjectError,'preferred candidate'):self.invoke(folder)

    def test_operating_input_tamper_even_rehashed_rejected(self):
        folder=self.copy();path=folder/'selected/operating/operating-network.json';data=json.loads(path.read_text());data['segments'][0]['length_m']=1.;path.write_text(json.dumps(data))
        self.rewrite(folder,lambda r:r['artifacts'].__setitem__('selected/operating/operating-network.json',digest(path)))
        with self.assertRaisesRegex(ProjectError,'sourced reconstruction'):self.invoke(folder)

    def test_artifact_coverage_and_replacement_curve_rejected(self):
        folder=self.copy();self.rewrite(folder,lambda r:r['artifacts'].pop('selected/curve.json'))
        with self.assertRaisesRegex(ProjectError,'coverage missing'):self.invoke(folder)
        plan=json.loads((EX/'fan-selected-plan.json').read_text());plan['tasks'][2]['curve']='fan-curve.json'
        staging=self.root/'plans';staging.mkdir()
        for p in EX.glob('*.json'):shutil.copyfile(p,staging/p.name)
        shutil.copyfile(EX/'brief.md',staging/'brief.md');path=staging/'fan-selected-plan.json';path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ProjectError,'replacement forbidden'):validate_plan(path)

    def test_no_feasible_selection_does_not_invoke_consumer(self):
        root=self.root/'no-feasible';root.mkdir()
        for p in EX.glob('*.json'):shutil.copyfile(p,root/p.name)
        shutil.copyfile(EX/'brief.md',root/'brief.md')
        path=root/'fan-catalogue.json';c=json.loads(path.read_text());c['candidates']=c['candidates'][:2];path.write_text(json.dumps(c))
        r=execute(root/'fan-selected-plan.json',root/'run')
        self.assertEqual(r['tasks']['fan']['status'],'fail')
        self.assertEqual(r['tasks']['selected-operation']['status'],'pending')
        self.assertFalse((root/'run/selected-operation').exists())
