import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import main
from bsa.workflow import verify

ROOT = Path(__file__).resolve().parents[1]


class UnifiedWorkflowTests(unittest.TestCase):
    def test_missing_engine_retains_diagnosis_and_blocks_native_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out = Path(folder)/'result'
            args = ['bsa', 'workflow', str(ROOT/'examples/shared-lighting-plan.json'), '--out', str(out)]
            with patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(main(), 2)
            summary = json.loads(stdout.getvalue())
            diagnosis = json.loads((out/'diagnosis.json').read_text(encoding='utf-8'))
            rows = {row['id']: row for row in diagnosis['tasks']}
            self.assertFalse(summary['design_accepted'])
            self.assertEqual(rows['native']['blocked_by'], ['shared'])
            self.assertFalse((out/'native').exists())
            self.assertTrue(verify(out)['integrity_pass'])
            original = (out/'workflow.json').read_bytes()
            with patch('sys.argv', args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main()
            self.assertEqual((out/'workflow.json').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
