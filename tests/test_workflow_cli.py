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
    def test_review_covers_all_requirements_without_approving_execution(self):
        from bsa.delivery import assess
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'result'
            review=Path(folder)/'review.json'
            plan=ROOT/'examples/drainage-preparation/plan.json'
            args=['bsa','workflow',str(plan),'--out',str(out),'--review',str(review)]
            with patch('sys.argv',args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(),2)
            rows=json.loads(review.read_text(encoding='utf-8'))['requirements']
            self.assertEqual({r['id'] for r in rows},{'R1','R2'})
            self.assertTrue(all(r['status']=='pending' for r in rows))
            audit=assess(plan,out,review)
            self.assertTrue(audit['source_integrity_pass'])
            self.assertFalse(audit['review_checks_pass'])
            self.assertFalse(audit['design_accepted'])

    def test_existing_or_internal_review_rejected_before_execution(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'result'
            existing=Path(folder)/'review.json'
            existing.write_text('keep',encoding='utf-8')
            for review in (existing,out/'review.json'):
                args=['bsa','workflow',str(ROOT/'examples/shared-lighting-plan.json'),
                      '--out',str(out),'--review',str(review)]
                with patch('sys.argv',args),contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):main()
                self.assertFalse(out.exists())
            self.assertEqual(existing.read_text(encoding='utf-8'),'keep')

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
