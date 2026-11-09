import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bsa.cli import digest
from bsa.delivery import template,assess,run,pointer
from bsa.engine import ProjectError
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]


class DeliveryReviewTests(unittest.TestCase):
    def test_manual_review_cannot_clear_its_required_pending_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            outer=Path(folder);plan,root,path,review=self.fixture(outer)
            data=json.loads(plan.read_text())
            data['tasks'][0]={'id':'electrical','kind':'manual','description':'Required upstream inspection'}
            data['tasks'][1]['requires_pass']=['electrical']
            plan.write_text(json.dumps(data))
            run_root=outer/'gated';execute(plan,run_root)
            review_path=outer/'gated-review.json';record=template(plan,run_root,review_path)
            # Manual inspection has no generated artifact; reuse a recorded HTML
            # artifact only to exercise reviewer assertions, not engineering proof.
            for row in record['requirements']:
                row.update(status='pass',reviewer='Test assertion',reviewed_at_utc='2026-11-09T00:00:00Z',
                           notes='Synthetic review assertion',evidence=[dict(artifact='index.html',sha256=digest(run_root/'index.html'))])
            review_path.write_text(json.dumps(record))
            result=assess(plan,run_root,review_path)
            self.assertEqual(result['requirements'][0]['effective_review_status'],'pass')
            self.assertEqual(result['requirements'][1]['effective_review_status'],'pending')
            self.assertEqual(result['requirements'][1]['blocked_by'],['electrical'])
            self.assertFalse(result['review_checks_pass'])

    def test_forged_passing_child_is_rejected_by_delivery_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            outer=Path(folder);plan=ROOT/'examples/shared-lighting-plan.json'
            root=outer/'run';execute(plan,root)
            report_path=root/'workflow.json';report=json.loads(report_path.read_text())
            report['tasks']['native']['status']='pass'
            for r in report['requirements']:
                if r['task']=='native':r['execution_status']='pass'
            report_path.write_text(json.dumps(report))
            path=outer/'review.json';template(plan,root,path)
            result=assess(plan,root,path)
            self.assertEqual(result['status'],'failed')
            self.assertTrue(any('nonpassing dependencies' in x for x in result['issues']))

    def test_versioned_example_keeps_missing_engineering_evidence_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan=ROOT/'examples/delivery-plan.json';execute(plan,root/'run')
            review_path=root/'review.json';template(plan,root/'run',review_path)
            result=assess(plan,root/'run',review_path)
            self.assertEqual(result['status'],'needs_review');self.assertEqual(len(result['requirements']),3)
            self.assertEqual(result['requirements'][2]['execution_status'],'pending')
            self.assertFalse(result['design_accepted'])

    def fixture(self,root,native=False):
        shutil.copyfile(ROOT/'examples/office-electrical/project.json',root/'project.json')
        brief=root/'brief.md';quote='Produce the conditional electrical results and review the delivered evidence.'
        brief.write_text(quote+'\n')
        tasks=[dict(id='electrical',kind='electrical',project='project.json'),
               dict(id='review',kind='native_cad',depends_on='electrical') if native else dict(id='review',kind='manual',description='Review actual evidence; not full engineering certification')]
        plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=tasks,
                  requirements=[dict(id='R'+str(i),passage='P001',quote=quote,task=t['id'],acceptance='Conditional result and cited evidence review; engineering acceptance separate') for i,t in enumerate(tasks)])
        path=root/'plan.json';path.write_text(json.dumps(plan));execute(path,root/'run')
        review_path=root/'review.json';review=template(path,root/'run',review_path)
        return path,root/'run',review_path,review

    def fill(self,root,review):
        artifact='electrical/calculations.json'
        for row in review['requirements']:
            row.update(status='pass',reviewer='Automated test fixture assertion',reviewed_at_utc='2026-11-08T00:00:00Z',
                       notes='Fixture exercises recorded review consistency; it does not certify an engineering design.',
                       evidence=[dict(artifact=artifact,sha256=digest(root/artifact))],
                       checks=[dict(artifact=artifact,pointer='/calculated_checks_pass',expected=True,basis='Conditional adapter checks requested by source requirement')])

    def test_template_pending_and_complete_scoped_assertions_never_certify_design(self):
        with tempfile.TemporaryDirectory() as folder:
            plan,root,path,review=self.fixture(Path(folder))
            result=assess(plan,root,path);self.assertEqual(result['status'],'needs_review')
            self.assertTrue(all(r['effective_review_status']=='pending' for r in result['requirements']))
            before=digest(root/'workflow.json');self.fill(root,review);path.write_text(json.dumps(review))
            result=run(plan,root,path,Path(folder)/'audit')
            self.assertTrue(result['review_checks_pass']);self.assertEqual(result['status'],'review_complete')
            self.assertFalse(result['design_accepted']);self.assertEqual(digest(root/'workflow.json'),before)
            self.assertTrue(verify(root)['integrity_pass'])

    def test_failed_boolean_fact_overrides_recorded_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            plan,root,path,review=self.fixture(Path(folder));self.fill(root,review)
            review['requirements'][0]['checks'][0]['pointer']='/design_accepted';path.write_text(json.dumps(review))
            result=assess(plan,root,path)
            self.assertEqual(result['status'],'failed');self.assertFalse(result['review_checks_pass'])
            self.assertFalse(result['requirements'][0]['facts'][0]['actual'])

    def test_missing_review_source_text_change_and_edited_run_matrix_fail(self):
        for action in ('missing','source','matrix','fingerprint','duplicate','locator'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
                plan,root,path,review=self.fixture(Path(folder));self.fill(root,review)
                if action=='missing':review['requirements'].pop()
                elif action=='fingerprint':review['requirements'][0]['requirement_sha256']='0'*64
                elif action=='duplicate':review['requirements'][1]['id']=review['requirements'][0]['id']
                elif action=='source':
                    p=json.loads(plan.read_text());p['requirements'][0]['acceptance']='An easier, different condition';plan.write_text(json.dumps(p))
                elif action=='locator':
                    p=json.loads((root/'workflow.json').read_text());p['requirements'][0]['source_locator']={'invented_page':999};(root/'workflow.json').write_text(json.dumps(p))
                else:
                    p=json.loads((root/'workflow.json').read_text());p['requirements'][0]['acceptance']='Unrecorded narrower review';(root/'workflow.json').write_text(json.dumps(p))
                path.write_text(json.dumps(review));result=assess(plan,root,path)
                self.assertEqual(result['status'],'failed');self.assertFalse(result['review_checks_pass'])

    def test_artifact_and_attachment_changes_are_not_hidden(self):
        for action in ('artifact','attachment','escape'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
                plan,root,path,review=self.fixture(Path(folder));self.fill(root,review)
                image=root/'supplemental.txt';image.write_text('Synthetic supplemental test evidence, not an actual rendered drawing')
                attachment=dict(path=image.name,sha256=digest(image),source_artifact='electrical/calculations.json',source_sha256=digest(root/'electrical/calculations.json'))
                review['requirements'][0]['attachments']=[attachment]
                if action=='artifact':
                    artifact=root/'electrical/calculations.json';artifact.write_bytes(artifact.read_bytes()+b'\n')
                elif action=='attachment':image.write_text('changed')
                else:attachment['path']='../review.json'
                path.write_text(json.dumps(review));result=assess(plan,root,path)
                self.assertEqual(result['status'],'failed');self.assertFalse(result['review_checks_pass'])

    def test_missing_engine_cannot_be_cleared_by_review_assertion(self):
        with tempfile.TemporaryDirectory() as folder:
            plan,root,path,review=self.fixture(Path(folder),native=True);self.fill(root,review);path.write_text(json.dumps(review))
            result=assess(plan,root,path)
            self.assertEqual(result['status'],'needs_review')
            self.assertEqual(result['requirements'][1]['effective_review_status'],'pending')

    def test_failed_task_cannot_be_cleared_and_outputs_do_not_overwrite_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            outer=Path(folder);plan,root,path,review=self.fixture(outer)
            with self.assertRaises(ProjectError):template(plan,root,root/'review.json')
            with self.assertRaises(ProjectError):run(plan,root,path,root/'audit')
            data=json.loads((outer/'project.json').read_text());data['circuits'][0]['breaker_a']=.1;(outer/'project.json').write_text(json.dumps(data))
            execute(plan,outer/'failed');failed=outer/'failed-review.json';review=template(plan,outer/'failed',failed)
            self.fill(outer/'failed',review)
            for row in review['requirements']:row['checks']=[]
            failed.write_text(json.dumps(review));result=assess(plan,outer/'failed',failed)
            self.assertEqual(result['requirements'][0]['effective_review_status'],'fail')

    def test_json_pointer_array_and_escape_rules(self):
        self.assertTrue(pointer({'a/b':[{'~field':True}]},'/a~1b/0/~0field'))
        for path in ('/a/-1','/a/01','/a/~2'):
            with self.assertRaises(ProjectError):pointer({'a':[True]},path)


if __name__=='__main__':unittest.main()
