from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from bsa.workflow import verify

ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'runs/hk-fan-sources-v1'


@unittest.skipUnless((CACHE/'emsd-bec-2024.pdf').is_file() and (CACHE/'emsd-tg-bec-2024.pdf').is_file(),'requires pinned official BEC/TG cache')
class RectangularHKDeliveryTests(unittest.TestCase):
    def test_missing_cad_and_nonpassing_rules_remain_distinct_blockers(self):
        stage=runpy.run_path(str(ROOT/'scripts/run_rectangular_hk_fan_demo.py'))
        module=types.ModuleType('run_rectangular_hk_fan_demo');module.stage=stage['stage'];module.ROOT=ROOT
        with patch.dict(sys.modules,{'run_rectangular_hk_fan_demo':module}):
            runner=runpy.run_path(str(ROOT/'scripts/run_rectangular_hk_fan_delivery.py'))['run']
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'delivery';result=runner(out,CACHE)
            rows={t['id']:t for t in result['tasks']}
            self.assertEqual(rows['model']['status'],'pass');self.assertEqual(rows['coordination']['status'],'pass')
            self.assertEqual(rows['pass']['status'],'pass');self.assertIn('AutoCAD',rows['pass-drawing']['recorded_scope'])
            for label in ('exceeded','unknown-supply'):
                self.assertIn(label,rows[label+'-drawing']['blocked_by'])
                self.assertIn('required checks unresolved',rows[label+'-drawing']['recorded_scope'])
                self.assertNotIn('AutoCAD',rows[label+'-drawing']['recorded_scope'])
            self.assertTrue(verify(out/'workflow')['integrity_pass'])
            self.assertTrue(all(not (out/'workflow'/(label+'-drawing')).exists() for label in ('pass','exceeded','unknown-supply')))
            self.assertFalse(result['design_accepted'])
