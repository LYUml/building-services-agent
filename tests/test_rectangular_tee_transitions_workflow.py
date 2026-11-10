import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bsa.cli import digest
from bsa.workflow import execute, validate_plan, verify
from bsa.engine import ProjectError

ROOT = Path(__file__).resolve().parents[1]


class TeeTransitionWorkflowTests(unittest.TestCase):
    def test_native_clash_handoff_actual_failure_and_no_replacement(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for source in (ROOT/'examples/rectangular-tee-transitions').glob('*'):
                if source.is_file(): shutil.copyfile(source, root/source.name)
            plan = root/'plan.json'; result = execute(plan, root/'positive')
            self.assertTrue(result['execution_pass'], result['tasks']); self.assertFalse(result['design_accepted'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            clash = json.loads((root/'positive/clash/clash.json').read_text())
            self.assertEqual(clash['inputs'][str(root/'positive/assembly/assembly.ifc')], digest(root/'positive/assembly/assembly.ifc'))
            self.assertEqual(clash['physical_element_count'], 3)
            self.assertEqual(len(clash['outside_region_checks']), 2)
            p = json.loads((root/'project.json').read_text()); p['arms']['main-b']['transition_length_m'] += .001
            (root/'project.json').write_text(json.dumps(p))
            failed = execute(plan, root/'failed')
            self.assertEqual(failed['tasks']['assembly']['status'], 'fail')
            self.assertEqual(failed['tasks']['clash']['status'], 'pending')
            self.assertFalse((root/'failed/clash').exists())
            p = json.loads(plan.read_text()); p['tasks'][0]['ifc'] = 'replacement.ifc'; plan.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError, 'replacement'): validate_plan(plan)
