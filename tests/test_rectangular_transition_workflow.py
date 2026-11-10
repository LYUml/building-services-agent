import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bsa.workflow import execute, validate_plan, verify
from bsa.engine import ProjectError
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class RectangularTransitionWorkflowTests(unittest.TestCase):
    def test_native_reader_source_pins_and_actual_producer_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for source in (ROOT/'examples/rectangular-transition').glob('*'):
                if source.is_file(): shutil.copyfile(source, root/source.name)
            plan = root/'plan.json'; result = execute(plan, root/'positive')
            self.assertTrue(result['execution_pass'], result['tasks']); self.assertFalse(result['design_accepted'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            preview = json.loads((root/'positive/preview/preview.json').read_text())
            self.assertEqual(preview['ifc_sha256'], digest(root/'positive/transition/transition.ifc'))
            self.assertEqual(preview['visual_review'], 'pending')
            data = json.loads((root/'project.json').read_text()); data['transition_length_m'] += .001
            (root/'project.json').write_text(json.dumps(data))
            failed = execute(plan, root/'failed')
            self.assertEqual(failed['tasks']['transition']['status'], 'fail')
            self.assertIn('length differs', failed['tasks']['transition']['scope'])
            self.assertEqual(failed['tasks']['preview']['status'], 'pending')
            self.assertFalse((root/'failed/preview').exists())
            self.assertTrue((root/'failed/transition/upstream.log').is_file())
            self.assertFalse(verify(root/'positive')['integrity_pass'])
            changed = json.loads(plan.read_text()); changed['tasks'][0]['ifc'] = 'replacement.ifc'
            plan.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ProjectError, 'replacement'): validate_plan(plan)
