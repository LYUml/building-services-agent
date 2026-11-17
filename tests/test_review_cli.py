"""Exercise the installed command contract against actual saved workflow evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'examples/delivery-plan.json'


class ReviewCLITests(unittest.TestCase):
    def call(self,*args):
        env=dict(os.environ);env.pop('BSA_PROJECT_ROOT',None)
        result=subprocess.run([sys.executable,'-m','bsa.cli',*map(str,args)],cwd=ROOT,
            env=env,capture_output=True,text=True,encoding='utf-8')
        self.assertNotIn('Traceback',result.stderr,result.stderr)
        return result

    def execute(self,root):
        run=root/'execution'
        result=self.call('workflow',PLAN,'--out',run)
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertFalse(json.loads(result.stdout)['execution_pass'])
        return run

    def test_integrity_status_and_pending_audit_preserve_original_evidence(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);run=self.execute(root)
            pins={p.relative_to(run).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in run.rglob('*') if p.is_file()}
            check=self.call('workflow-verify',run)
            self.assertEqual(check.returncode,0,check.stderr)
            self.assertTrue(json.loads(check.stdout)['integrity_pass'])
            state=self.call('workflow-status',PLAN,run)
            self.assertEqual(state.returncode,2,state.stderr)
            diagnosis=json.loads(state.stdout)
            self.assertFalse(diagnosis['execution_pass']);self.assertFalse(diagnosis['design_accepted'])
            self.assertEqual({t['id']:t['status'] for t in diagnosis['tasks']},
                dict(electrical='pass',visual='pending',faults='pending'))
            review=root/'review.json'
            result=self.call('delivery','template',PLAN,run,'--out',review)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['requirement_count'],3)
            audit=self.call('delivery','audit',PLAN,run,'--review',review,'--out',root/'audit')
            self.assertEqual(audit.returncode,2,audit.stderr)
            self.assertEqual(json.loads(audit.stdout)['status'],'needs_review')
            saved=json.loads((root/'audit/audit.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['review_agenda']['remaining_requirement_count'],3)
            self.assertFalse(saved['design_accepted'])
            self.assertTrue((root/'audit/report.html').is_file())
            self.assertEqual(pins,{p.relative_to(run).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in run.rglob('*') if p.is_file()})

    def test_changed_artifacts_are_not_integrity_or_delivery_success(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);run=self.execute(root)
            path=run/'electrical/calculations.json';path.write_text('{}',encoding='utf-8')
            result=self.call('workflow-verify',run)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertFalse(json.loads(result.stdout)['integrity_pass'])
            result=self.call('delivery','template',PLAN,run,'--out',root/'review.json')
            self.assertEqual(result.returncode,2)
            self.assertFalse((root/'review.json').exists())

    def test_review_cannot_overwrite_or_escape_workspace(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory, tempfile.TemporaryDirectory() as outside:
            root=Path(directory);run=self.execute(root);review=root/'review.json'
            result=self.call('delivery','template',PLAN,run,'--out',review)
            self.assertEqual(result.returncode,0,result.stderr);before=review.read_bytes()
            result=self.call('delivery','template',PLAN,run,'--out',review)
            self.assertEqual(result.returncode,2);self.assertEqual(review.read_bytes(),before)
            result=self.call('delivery','audit',PLAN,run,'--review',review,'--out',run/'audit')
            self.assertEqual(result.returncode,2);self.assertFalse((run/'audit').exists())
            escaped=Path(outside)/'review.json'
            result=self.call('delivery','template',PLAN,run,'--out',escaped)
            self.assertEqual(result.returncode,2);self.assertFalse(escaped.exists())

    def test_malformed_saved_report_returns_a_scoped_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);run=root/'execution';run.mkdir()
            (run/'workflow.json').write_text('{}',encoding='utf-8')
            for args in [('workflow-verify',run),('workflow-status',PLAN,run),
                ('delivery','template',PLAN,run,'--out',root/'review.json')]:
                with self.subTest(command=args[0]):
                    result=self.call(*args)
                    self.assertEqual(result.returncode,2)
            self.assertFalse((root/'review.json').exists())


if __name__=='__main__':unittest.main()
