import json
import shutil
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.rectangular_fan_selection import mechanical_context
from bsa.workflow import verify
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];PDF=ROOT/'runs/tcf-fan-intake-v1/tcf-m300.pdf'

@unittest.skipUnless(PDF.is_file(),'requires pinned official manufacturer PDF cache')
class FanMechanicalSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.runner=runpy.run_path(str(ROOT/'scripts/run_fan_mechanical_selection_demo.py'))
        cls.result=cls.runner['run'](cls.root/'cases',PDF)

    def test_overspeed_is_rejected_before_ranking_and_alternative_replayed(self):
        row=self.result['cases']['overspeed-first'];self.assertEqual(row['selected'],'second');self.assertEqual(row['states']['selected-operation'],'pass')
        report=json.loads((self.root/'cases/overspeed-first/workflow/fan/fan-selection.json').read_text())
        self.assertTrue(report['candidates'][0]['numerical_checks_pass']);self.assertFalse(report['candidates'][0]['calculated_checks_pass']);self.assertEqual(report['candidates'][0]['mechanical']['status'],'fail')
        self.assertTrue(verify(self.root/'cases/overspeed-first/workflow')['integrity_pass'])

    def test_unknown_preference_is_preserved_instead_of_silently_skipped(self):
        row=self.result['cases']['preferred-unknown'];self.assertEqual(row['states']['fan'],'pending');self.assertIsNone(row['selected']);self.assertEqual(row['unresolved_preference'],['first'])
        row=self.result['cases']['lower-unknown'];self.assertEqual(row['selected'],'first');self.assertEqual(row['states']['selected-operation'],'pass')

    def test_all_known_overspeed_has_no_selection(self):
        row=self.result['cases']['all-overspeed'];self.assertEqual(row['states']['fan'],'fail');self.assertIsNone(row['selected'])

    def test_source_coverage_path_and_changed_table_reject(self):
        root=self.root/'invalid';path=self.runner['stage'](root,PDF,'overspeed-first');catalogue=root/'fan-catalogue.json';original=catalogue.read_text();c=json.loads(original)
        c['mechanical']['classes'].pop('first');catalogue.write_text(json.dumps(c))
        with self.assertRaisesRegex(ProjectError,'complete'):mechanical_context(catalogue)
        c=json.loads(original);c['mechanical']['record']='../outside.json';catalogue.write_text(json.dumps(c))
        with self.assertRaisesRegex(ProjectError,'inside'):mechanical_context(catalogue)
        catalogue.write_text(original);record=root/'product.json';r=json.loads(record.read_text());r['published_data']['maximum_speed_rpm']['Class_I']=9999;record.write_text(json.dumps(r))
        with self.assertRaisesRegex(ProjectError,'independently extracted'):mechanical_context(catalogue)

    def test_handoff_reconstructs_mechanical_eligibility(self):
        from bsa.rectangular_fan_selection import selected_input
        case=self.root/'cases/overspeed-first';copy=self.root/'forged-selection'
        shutil.copytree(case/'workflow/fan',copy)
        report=copy/'fan-selection.json';r=json.loads(report.read_text())
        r['candidates'][0]['mechanical']['status']='pass';r['candidates'][0]['calculated_checks_pass']=True
        report.write_text(json.dumps(r));base=case/'workflow/air'
        with self.assertRaisesRegex(ProjectError,'fresh fan solve'):
            selected_input(copy,base/'network-input.json',case/'elbow-chain-model.json',case/'elbow-chain-binding.json',base/'bim/model.ifc',base/'analysis/network.json',case/'fan-catalogue.json')
