import json
from pathlib import Path
import tempfile
import unittest
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]


class CirculationClashGateTests(unittest.TestCase):
    def test_hydraulic_pass_does_not_release_overlapping_geometry(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            out=Path(tmp)/'workflow'
            result=execute(ROOT/'examples/circulation-ifc/coordination-plan.json',out)
            self.assertEqual(result['tasks']['water']['status'],'pass')
            self.assertEqual(result['tasks']['clash']['status'],'fail')
            self.assertEqual(result['tasks']['drawing']['status'],'pending')
            self.assertFalse((out/'drawing').exists())
            clash=json.loads((out/'clash/clash.json').read_text())
            self.assertTrue(clash['checks']['geometry_coverage'])
            overlaps=[r for r in clash['intersections'] if r.get('overlap_volume_m3',0)>1e-10]
            self.assertTrue(any(set(r['names'])=={'PUMP','N_SUCTION'} for r in overlaps))
            self.assertTrue(verify(out)['integrity_pass'])
            self.assertFalse(result['design_accepted'])
