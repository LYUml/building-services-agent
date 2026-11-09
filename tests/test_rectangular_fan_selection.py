import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.rectangular_binding import run as bind
from bsa.rectangular_fan_selection import run,candidates
from bsa.workflow import execute,verify,validate_plan
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'

class RectangularFanSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name);cls.base=cls.root/'producer'
        bind(EX/'elbow-chain-project.json',EX/'elbow-chain-model.json',EX/'elbow-chain-binding.json',cls.base)

    def invoke(self,catalogue=None):
        return run(self.base/'network-input.json',EX/'elbow-chain-model.json',EX/'elbow-chain-binding.json',self.base/'bim/model.ifc',self.base/'analysis/network.json',catalogue or EX/'fan-catalogue.json',self.root/self._testMethodName)

    def catalogue(self,data):
        path=self.root/(self._testMethodName+'.json');path.write_text(json.dumps(data));return path

    def test_retains_rejections_and_reruns_preferred_passing_candidate(self):
        r=self.invoke();self.assertTrue(r['calculated_checks_pass']);self.assertEqual(r['selected']['id'],'supported')
        self.assertEqual([c['status'] for c in r['candidates']],['not_bracketed','unsupported','converged'])
        self.assertIn('fluid mismatch',r['candidates'][1]['reason']);self.assertTrue(r['selected_rerun_pass'])
        self.assertEqual(r['selected']['rerun']['operating_point'],r['candidates'][2]['operating_point'])
        self.assertFalse(r['design_accepted'])

    def test_no_feasible_has_no_selected_output(self):
        data=json.loads((EX/'fan-catalogue.json').read_text());data['candidates']=data['candidates'][:2]
        r=self.invoke(self.catalogue(data));self.assertFalse(r['feasible_candidate_found']);self.assertFalse(r['calculated_checks_pass']);self.assertIsNone(r['selected'])
        self.assertFalse((self.root/self._testMethodName/'selected').exists())

    def test_preference_and_lexical_tie_break_are_explicit(self):
        data=json.loads((EX/'fan-catalogue.json').read_text());good=data['candidates'][-1]
        other=copy.deepcopy(good);other['id']='aaa';data['candidates']=[good,other]
        r=self.invoke(self.catalogue(data));self.assertEqual(r['selected']['id'],'aaa')

    def test_invalid_catalogue_rejects_before_runs(self):
        data=json.loads((EX/'fan-catalogue.json').read_text())
        for mode in ('duplicate','boolean','static'):
            c=copy.deepcopy(data)
            if mode=='duplicate':c['candidates'][1]['id']=c['candidates'][0]['id']
            if mode=='boolean':c['candidates'][0]['preference']=True
            if mode=='static':c['candidates'][0]['curve']['pressure_basis']='static'
            with self.subTest(mode=mode),self.assertRaises(ProjectError):candidates(c)

    def test_workflow_no_feasible_blocks_review_and_tracks_artifacts(self):
        root=self.root/'workflow';root.mkdir()
        for p in EX.glob('*.json'):shutil.copyfile(p,root/p.name)
        shutil.copyfile(EX/'brief.md',root/'brief.md');plan=root/'fan-selection-plan.json'
        result=execute(plan,root/'pass');self.assertEqual(result['tasks']['fan']['status'],'pass')
        self.assertTrue(verify(root/'pass')['integrity_pass'])
        artifact=root/'pass/fan/selected/curve.json';artifact.write_text('{}');self.assertFalse(verify(root/'pass')['integrity_pass'])
        catalogue=root/'fan-catalogue.json';c=json.loads(catalogue.read_text());c['candidates']=c['candidates'][:2];catalogue.write_text(json.dumps(c))
        result=execute(plan,root/'fail');self.assertEqual(result['tasks']['fan']['status'],'fail')
        self.assertIn('required checks unresolved',result['tasks']['review']['scope'])
        self.assertFalse((root/'fail/fan/selected').exists())
        p=json.loads(plan.read_text());p['tasks'][1]['project']='fan-project.json';plan.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'replacements forbidden'):validate_plan(plan)
