import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from bsa.workflow import execute, validate_plan, verify
from bsa.engine import ProjectError
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class RectangularTeeWorkflowTests(unittest.TestCase):
    def test_connected_native_handoff_and_failure_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for source in (ROOT/'examples/rectangular-tee').glob('*'):
                if source.is_file():
                    shutil.copyfile(source, root/source.name)
            plan = root/'assembly-plan.json'
            result = execute(plan, root/'positive')
            self.assertTrue(result['execution_pass'], result['tasks'])
            self.assertFalse(result['design_accepted'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            self.assertEqual(result['inputs'][str(root/'assembly.json')], digest(root/'assembly.json'))
            with patch('bsa.rectangular_tee_assembly.run', side_effect=ValueError('native assembly rejected')):
                failed = execute(plan, root/'failed')
            self.assertEqual(failed['tasks']['assembly']['status'], 'fail')
            self.assertEqual(failed['tasks']['clash']['status'], 'pending')
            self.assertFalse((root/'failed/clash').exists())
            data = json.loads(plan.read_text())
            data['tasks'][0]['ifc'] = 'replacement.ifc'
            plan.write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError, 'replacement'):
                validate_plan(plan)

    def test_native_handoff_integrity_and_failure_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for source in (ROOT/'examples/rectangular-tee').glob('*'):
                if source.is_file():
                    shutil.copyfile(source, root/source.name)
            plan = root/'plan.json'
            result = execute(plan, root/'positive')
            self.assertEqual(result['tasks']['tee']['status'], 'pass')
            self.assertEqual(result['tasks']['clash']['status'], 'fail')
            self.assertIn('at least two represented physical elements', result['tasks']['clash']['scope'])
            self.assertFalse(result['execution_pass'])
            self.assertFalse(result['design_accepted'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            with patch('bsa.rectangular_tee.run', side_effect=ValueError('native check rejected')):
                failed = execute(plan, root/'failed')
            self.assertEqual(failed['tasks']['tee']['status'], 'fail')
            self.assertEqual(failed['tasks']['clash']['status'], 'pending')
            self.assertFalse((root/'failed/clash').exists())
            data = json.loads(plan.read_text())
            data['tasks'][0]['ifc'] = 'replacement.ifc'
            plan.write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError, 'replacement'):
                validate_plan(plan)
            (root/'positive/tee/rectangular-tee.ifc').write_text('changed')
            self.assertFalse(verify(root/'positive')['integrity_pass'])
