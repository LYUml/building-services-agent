import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from bsa.engine import ProjectError
from bsa.workflow import validate_plan,execute
from bsa.workflow_draft import draft
from bsa.workflow_status import diagnose
from bsa.delivery import template,assess

ROOT=Path(__file__).resolve().parents[1]


class WorkflowDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.brief=self.root/'brief.md';self.out=self.root/'plan.json'
        self.brief.write_text('Design the water system.\n\nReport electrical kW and thermal kW separately.\n',encoding='utf-8')

    def test_complete_bundle_is_preserved_and_execution_stays_blocked(self):
        rubric=self.root/'rubric.md';rubric.write_text('提交可编辑模型和计算报告。',encoding='utf-8')
        result=draft(self.brief,self.out,[rubric])
        source,_=validate_plan(self.out)
        self.assertEqual(result['passages'],3)
        self.assertEqual(source['requirements'][-1]['passage'],'D002:P001')
        self.assertEqual(source['requirements'][-1]['quote'],'提交可编辑模型和计算报告。')
        execute(self.out,self.root/'run')
        report=diagnose(self.out,self.root/'run')
        self.assertEqual(len(report['actions']),3)
        self.assertTrue(all(a['input_blockers'] for a in report['actions']))
        review=self.root/'review.json';template(self.out,self.root/'run',review)
        data=json.loads(review.read_text());
        for row in data['requirements']:row['status']='pass'
        review.write_text(json.dumps(data),encoding='utf-8')
        self.assertFalse(assess(self.out,self.root/'run',review)['review_checks_pass'])

    def test_sources_unchanged_and_existing_plan_not_overwritten(self):
        before=self.brief.read_bytes();draft(self.brief,self.out);saved=self.out.read_bytes()
        with self.assertRaises(ProjectError):draft(self.brief,self.out)
        self.assertEqual(self.out.read_bytes(),saved);self.assertEqual(self.brief.read_bytes(),before)

    def test_changed_source_invalidates_draft(self):
        draft(self.brief,self.out);self.brief.write_text('Changed actual requirement.',encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'hash differs'):validate_plan(self.out)

    def test_sources_outside_plan_tree_rejected(self):
        with self.assertRaisesRegex(ProjectError,'under the plan directory'):draft(self.brief,self.root/'nested/plan.json')

    def test_empty_source_cannot_create_false_coverage(self):
        self.brief.write_text('',encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'no extracted passages'):draft(self.brief,self.out)
        self.assertFalse(self.out.exists())

    def test_extraction_review_is_not_acknowledged_by_drafting(self):
        # Minimal parser fixture, not a rendered deliverable.
        doc=self.root/'brief.docx'
        with zipfile.ZipFile(doc,'w') as archive:
            archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Inspect the supplied diagram.</w:t><w:drawing/></w:r></w:p></w:body></w:document>')
        result=draft(doc,self.out)
        self.assertTrue(result['extraction_issues'])
        self.assertEqual(json.loads(self.out.read_text())['document_review'],{})
        with self.assertRaisesRegex(ProjectError,'inspection note'):validate_plan(self.out)
