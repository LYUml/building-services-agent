import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from bsa.project_start import start
from bsa.workflow import validate_plan

ROOT=Path(__file__).resolve().parents[1]


class ProjectStartTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.brief=self.root/'brief.md';self.brief.write_text('Calculate supply airflow.\n\nProvide editable drawings.')

    def test_source_bundle_preserves_quotes_and_waits_for_interpretation(self):
        supplement=self.root/'rubric.txt';supplement.write_text('Keep thermal and electrical power separate.')
        before=self.brief.read_bytes();out=self.root/'project';r=start(self.brief,out,supplements=[supplement])
        self.assertEqual(r['status'],'needs_interpretation');self.assertTrue(r['interpretation_template_ready'])
        p,_=validate_plan(out/'plan.json');self.assertEqual(len(p['requirements']),3)
        self.assertTrue(all(t['kind']=='manual' for t in p['tasks']));self.assertEqual(len(p['unresolved_inputs']),3)
        self.assertEqual(self.brief.read_bytes(),before);self.assertFalse(r['design_accepted'])
        self.assertEqual(json.loads((out/'work-review.json').read_text())['tasks'],[])

    def test_empty_source_is_retained_without_false_plan(self):
        self.brief.write_text('');out=self.root/'empty';r=start(self.brief,out)
        self.assertEqual(r['status'],'needs_source_review');self.assertTrue(r['stage_errors'])
        self.assertFalse((out/'plan.json').exists());self.assertTrue((out/'intake.json').exists())

    def test_explicit_reference_retains_context_and_supplement_requirements(self):
        supplement=self.root/'rubric.md';supplement.write_text('Provide calculations.')
        reference=self.root/'guide.md';reference.write_text('General hotel example.\n\nGeneral fan selection procedure.')
        out=self.root/'roles';r=start(self.brief,out,supplements=[supplement],references=[reference])
        self.assertEqual(r['effective_plan'],'role-plan.json');self.assertTrue(r['interpretation_template_ready'])
        plan,inputs=validate_plan(out/'role-plan.json')
        self.assertEqual(len(plan['requirements']),3)
        self.assertEqual(plan['passage_dispositions']['D003:P001'],'context')
        self.assertEqual(plan['passage_dispositions']['D002:P001'],'requirement')
        self.assertEqual(len(json.loads((out/'plan.json').read_text())['requirements']),5)
        self.assertIn((out/'source-roles.json').resolve(),inputs)
        self.assertEqual([x['role'] for x in r['sources']],['primary','supplement','reference'])
        self.assertEqual(len(json.loads((out/'work-review.json').read_text())['passages']),3)
        (out/r['sources'][-1]['staged']).write_text('Changed reference bytes')
        with self.assertRaises(ValueError):validate_plan(out/'role-plan.json')

    def test_overwrite_duplicate_and_unsupported_sources_reject(self):
        out=self.root/'existing';out.mkdir()
        with self.assertRaises(ValueError):start(self.brief,out)
        with self.assertRaises(ValueError):start(self.brief,self.root/'duplicate',supplements=[self.brief])
        bad=self.root/'brief.exe';bad.write_bytes(b'Not an executable input')
        with self.assertRaises(ValueError):start(bad,self.root/'bad')

    def test_reference_role_does_not_acknowledge_graphical_extraction(self):
        reference=self.root/'diagram.docx'
        with zipfile.ZipFile(reference,'w') as archive:
            archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Reference diagram.</w:t><w:drawing/></w:r></w:p></w:body></w:document>')
        out=self.root/'graphical';r=start(self.brief,out,references=[reference])
        self.assertEqual(r['status'],'needs_source_review');self.assertFalse(r['interpretation_template_ready'])
        plan=json.loads((out/'role-plan.json').read_text());self.assertEqual(plan['document_review'],{})
        self.assertEqual(plan['passage_dispositions']['D002:P001'],'context')
        self.assertFalse((out/'work-review.json').exists())
