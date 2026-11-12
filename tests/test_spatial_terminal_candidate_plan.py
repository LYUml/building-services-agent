import copy
import json
import unittest
from bsa.spatial_terminal_revision import run as study
from bsa.spatial_terminal_candidate_plan import run,verify as verify_plan
from bsa.workflow import execute,verify
from bsa.delivery import context
from tests import test_spatial_terminal_performance as fixtures

class CandidatePlanTests(unittest.TestCase):
    def test_full_plan_preserved_and_reexecuted(self):
        fixture=fixtures.SpatialTerminalPerformanceTests();fixture.setUp();self.addCleanup(fixture.temp.cleanup)
        out,_=fixture.run_workflow();original=json.loads(fixture.plan.read_text());before=fixture.plan.read_bytes()
        candidate=fixture.root/'candidate';study(out/'terminal-performance/terminal-performance.json',fixture.plan.parent/'terminal-design-basis.json',fixture.plan.parent/'performance-selections.json',candidate)
        target=fixture.plan.parent/'candidate-plan.json';result=run(fixture.plan,candidate,'terminal-performance',target)
        new=json.loads(target.read_text());expected=copy.deepcopy(original)
        for row in expected['tasks']:
            if row['id']=='terminal-allocation':row['basis']='candidate-plan-inputs/terminal-basis.json'
            if row['id']=='terminal-performance':row['basis']='candidate-plan-inputs/products.json'
        self.assertEqual(new,expected);self.assertEqual(fixture.plan.read_bytes(),before);self.assertTrue(result['requirements_preserved']);self.assertFalse(result['design_accepted'])
        rerun=fixture.root/'rerun';record=execute(target,rerun,module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        self.assertTrue(verify(rerun)['integrity_pass']);context(target,rerun)
        self.assertEqual(record['tasks']['terminal-performance']['status'],'pass');self.assertEqual(record['tasks']['review']['status'],'pending')
        with self.assertRaises(ValueError):run(fixture.plan,candidate,'terminal-performance',target)
        with self.assertRaises(ValueError):run(fixture.plan,candidate,'lighting-rules',fixture.plan.parent/'wrong.json')

        data=json.loads(target.read_text());data['requirements'][0]['acceptance']='Silently weakened';target.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'pins differ'):verify_plan(target)
