import copy
import json
from pathlib import Path
import tempfile
import unittest

from bsa.cli import digest
from bsa.delivery import assess,template
from bsa.engine import ProjectError
from bsa.workflow import execute,validate_plan
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class InputIssueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.texts=['Prepare the supplied synthetic overlay.',
                    'Verify installation conditions before sizing.',
                    'Deliver only after sizing verification.']
        brief=self.root/'brief.md';brief.write_text('\n\n'.join(self.texts),encoding='utf-8')
        (self.root/'project.json').write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
        self.issue=dict(id='installation',kind='missing',description='Installation conditions are not established by this fixture.',
            sources=[dict(passage='P002',quote=self.texts[1])],blocks_tasks=['sizing','manual'])
        self.spec=dict(version=1,brief='brief.md',brief_sha256=digest(brief),
            passage_dispositions={f'P{i:03}':'requirement' for i in range(1,4)},
            unresolved_inputs=[self.issue],tasks=[
                dict(id='independent',kind='electrical',project='project.json'),
                dict(id='sizing',kind='electrical',project='project.json'),
                dict(id='release',kind='manual',requires_pass=['sizing']),
                dict(id='manual',kind='manual')],
            requirements=[dict(id='R'+str(i),passage=f'P{p:03}',quote=self.texts[p-1],task=t,
                acceptance='Scoped synthetic test only') for i,(p,t) in enumerate(
                    [(1,'independent'),(2,'sizing'),(3,'release'),(2,'manual')],1)])
        self.plan=self.root/'plan.json';self.save()

    def save(self):self.plan.write_text(json.dumps(self.spec),encoding='utf-8')

    def test_missing_inputs_block_adapter_and_release_but_not_independent_task(self):
        run=self.root/'run';result=execute(self.plan,run)
        self.assertEqual(result['tasks']['independent']['status'],'pass')
        self.assertEqual(result['tasks']['sizing']['status'],'pending')
        page=(run/'index.html').read_text(encoding='utf-8')
        self.assertIn('Unresolved design inputs',page)
        self.assertIn(self.issue['description'],page)
        self.assertFalse((run/'sizing').exists());self.assertFalse((run/'release').exists())
        rows={r['id']:r for r in diagnose(self.plan,run)['tasks']}
        self.assertEqual(rows['sizing']['input_blockers'],[self.issue])
        self.assertEqual(rows['release']['upstream_action_tasks'],['sizing'])
        self.assertIn('missing/conflicting',rows['sizing']['next_action'])
        review=self.root/'review.json';template(self.plan,run,review)
        data=json.loads(review.read_text(encoding='utf-8'))
        data['requirements'][3].update(status='pass',reviewer='Synthetic test reviewer',
            reviewed_at_utc='2026-11-09T00:00:00Z',notes='Test assertion must not clear missing input.',
            evidence=[dict(artifact='independent/calculations.json',sha256=result['artifact_hashes']['independent/calculations.json'])])
        review.write_text(json.dumps(data),encoding='utf-8')
        audited=assess(self.plan,run,review)
        self.assertEqual(audited['requirements'][3]['effective_review_status'],'pending')
        self.assertEqual(audited['requirements'][3]['input_blockers'],[self.issue])
        self.assertFalse(audited['design_accepted'])

    def test_forged_pass_or_erased_register_cannot_clear_gate(self):
        run=self.root/'run';result=execute(self.plan,run)
        report_path=run/'workflow.json'
        result['tasks']['manual']['status']='pass'
        for row in result['requirements']:
            if row['task']=='manual':row['execution_status']='pass'
        report_path.write_text(json.dumps(result),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'unresolved design inputs'):diagnose(self.plan,run)
        result['unresolved_inputs']=[]
        report_path.write_text(json.dumps(result),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'register differs'):diagnose(self.plan,run)

    def test_bad_citations_targets_and_conflict_without_two_sources_rejected(self):
        original=copy.deepcopy(self.issue)
        for change in (dict(sources=[dict(passage='P002',quote='invented data')]),
                       dict(blocks_tasks=['unknown']),dict(blocks_tasks=['sizing','sizing']),
                       dict(kind='resolved'),dict(kind='conflict'),dict(id='../escape')):
            self.spec['unresolved_inputs']=[dict(original,**change)];self.save()
            with self.assertRaises(ProjectError):validate_plan(self.plan)
        self.spec['unresolved_inputs']=[dict(original,kind='conflict',sources=[
            dict(passage='P001',quote=self.texts[0]),dict(passage='P002',quote=self.texts[1])])]
        self.save();validate_plan(self.plan)


if __name__=='__main__':unittest.main()
