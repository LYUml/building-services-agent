import copy
import json
import unittest
from bsa.spatial_terminal_revision import run,verify
from tests import test_spatial_terminal_performance as fixtures

class SpatialTerminalRevisionTests(unittest.TestCase):
    def test_preserved_baseline_source_replay_and_tamper(self):
        fixture=fixtures.SpatialTerminalPerformanceTests();fixture.setUp();self.addCleanup(fixture.temp.cleanup)
        out,_=fixture.run_workflow();baseline=out/'terminal-performance/terminal-performance.json';original=baseline.read_bytes()
        basis=fixture.root/'candidate-basis.json';basis.write_bytes((fixture.plan.parent/'terminal-design-basis.json').read_bytes())
        products=fixture.plan.parent/'performance-selections.json'
        result=run(baseline,basis,products,fixture.root/'candidate')
        self.assertEqual(result['comparison']['original_maximum_flow_L_s'],result['comparison']['candidate_maximum_flow_L_s'])
        self.assertTrue(result['comparison']['catalogue_range_covered']);self.assertFalse(result['design_accepted']);self.assertEqual(baseline.read_bytes(),original)
        report=fixture.root/'candidate/candidate-comparison.json';changed=copy.deepcopy(result);changed['comparison']['candidate_terminal_count']+=1;report.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'differs from replay'):verify(report.parent)
        with self.assertRaises(ValueError):run(baseline,basis,products,fixture.root/'candidate')
