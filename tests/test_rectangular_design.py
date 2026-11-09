import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.rectangular_design import search,run
from bsa.rectangular_network import calculate
from bsa.workflow import execute,verify
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/rectangular-air'


class RectangularDesignTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((EXAMPLE/'undersized.json').read_text())
        self.c=json.loads((EXAMPLE/'catalogue.json').read_text())

    def test_retains_baseline_rejections_and_independent_velocity_lower_bound(self):
        before=copy.deepcopy(self.p);r,selected=search(self.p,self.c)
        self.assertFalse(calculate(self.p)['calculated_checks_pass'])
        self.assertEqual(r['candidate_count'],27);self.assertTrue(r['search_complete'])
        self.assertTrue(any(not row['feasible'] for row in r['candidates']))
        # MAIN Q=.5 needs A>=.5/7; medium A=.06 cannot qualify.
        self.assertEqual(r['selected']['choices']['MAIN'],'large')
        self.assertEqual(r['selected']['choices']['BR-A'],'medium')
        self.assertEqual(r['selected']['choices']['BR-B'],'medium')
        expected=8*3+5*2+10*2
        self.assertEqual(r['selected']['material_score'],expected)
        self.assertTrue(calculate(selected)['calculated_checks_pass'])
        self.assertEqual(self.p,before)
        self.assertEqual(selected['segments'][0]['minor_k'],before['segments'][0]['minor_k'])

    def test_no_feasible_does_not_return_a_selected_network(self):
        for key in self.c['allowed_options']:self.c['allowed_options'][key]=['small']
        r,selected=search(self.p,self.c)
        self.assertFalse(r['feasible_design_found']);self.assertIsNone(selected)

    def test_bounds_and_circular_options_rejected(self):
        self.c['max_evaluations']=26
        with self.assertRaisesRegex(ProjectError,'exceed'):search(self.p,self.c)
        self.c['max_evaluations']=27;self.c['options'][0]['diameter_m']=.1
        with self.assertRaises(ProjectError):search(self.p,self.c)

    def test_selected_dimensions_are_saved_and_freshly_rerun(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'design';r=run(EXAMPLE/'undersized.json',EXAMPLE/'catalogue.json',out)
            self.assertTrue(r['selected_rerun_pass']);self.assertFalse(r['baseline']['calculated_checks_pass'])
            selected=json.loads((out/'selected-network.json').read_text())
            self.assertEqual(selected['segments'][0]['width_m'],.5)
            self.assertIn('sizing/segment/MAIN',selected['sources'])
            report=json.loads((out/'selected/network.json').read_text())
            self.assertTrue(report['calculated_checks_pass']);self.assertFalse(report['geometry_bound'])

    def test_workflow_keeps_manual_review_and_hashes_all_engines(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'run';plan=EXAMPLE/'design-plan.json';execute(plan,out)
            r=diagnose(plan,out);self.assertEqual([t['status'] for t in r['tasks']],['pass','pending'])
            self.assertTrue(verify(out)['integrity_pass'])
            inputs=json.loads((out/'workflow.json').read_text())['inputs']
            for name in ('rectangular_design','rectangular_network','network_design','network'):
                self.assertIn(str(ROOT/f'src/bsa/{name}.py'),inputs)

    def test_no_feasible_workflow_blocks_review_and_writes_no_selected_model(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder)
            for name in ('brief.md','undersized.json','design-plan.json'):(root/name).write_bytes((EXAMPLE/name).read_bytes())
            for key in self.c['allowed_options']:self.c['allowed_options'][key]=['small']
            (root/'catalogue.json').write_text(json.dumps(self.c),encoding='utf-8')
            execute(root/'design-plan.json',root/'run')
            rows=diagnose(root/'design-plan.json',root/'run')['tasks']
            self.assertEqual([t['status'] for t in rows],['fail','pending'])
            self.assertEqual(rows[1]['blocked_by'],['air'])
            self.assertFalse((root/'run/air/selected-network.json').exists())
