from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.workflow import execute,validate_plan,verify

ROOT=Path(__file__).resolve().parents[1]


class RouteWorkflowTests(unittest.TestCase):
    def test_route_inputs_are_tracked_and_failed_pressure_blocks_clash(self):
        plan=ROOT/'examples/route-search/coordination-plan.json'
        _,inputs=validate_plan(plan)
        for name in ('route-input.json','model-settings.json','network.json','self-clash-policy.json'):
            self.assertIn((plan.parent/name).resolve(),inputs)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            with patch('bsa.route_optimize.run',return_value={'calculated_checks_pass':False}),patch('bsa.clash.run',side_effect=AssertionError('failed producer must block clash')) as clash:
                result=execute(plan,Path(folder)/'run')
            clash.assert_not_called()
            self.assertEqual(result['tasks']['route']['status'],'fail')
            self.assertEqual(result['tasks']['self-qa']['status'],'pending')
            self.assertEqual(result['tasks']['review']['status'],'pending')
            self.assertTrue(verify(Path(folder)/'run')['integrity_pass'])

    def test_passing_producer_uses_registered_selected_ifc_path(self):
        plan=ROOT/'examples/route-search/coordination-plan.json'
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=(Path(folder)/'run').resolve()
            with patch('bsa.route_optimize.run',return_value={'calculated_checks_pass':True}),patch('bsa.clash.run',return_value={'calculated_checks_pass':True}) as clash:
                result=execute(plan,out)
            self.assertEqual(clash.call_args.args[0],out/'route/selected/bound/bim/model.ifc')
            self.assertEqual(result['tasks']['self-qa']['status'],'pass')
            self.assertFalse(result['design_accepted'])
