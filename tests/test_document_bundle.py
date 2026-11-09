"""Multi-source coverage and evidence tests; no engineering interpretation claim."""
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

from bsa.cli import digest
from bsa.delivery import template,assess
from bsa.engine import ProjectError
from bsa.workflow import intake,execute,validate_plan,plan_documents
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.brief=self.root/'brief.md'
        self.brief.write_text('Provide editable MEP drawings.',encoding='utf-8')
        self.rubric=self.root/'rubric.md'
        self.rubric.write_text('Include performance calculations and source references.',encoding='utf-8')
        self.spec=dict(version=1,brief='brief.md',brief_sha256=digest(self.brief),
            supplemental_briefs=[dict(brief='rubric.md',brief_sha256=digest(self.rubric))],
            passage_dispositions={'P001':'requirement','D002:P001':'requirement'},
            tasks=[dict(id='review',kind='manual',description='Full engineering/visual verification pending')],
            requirements=[dict(id='R1',passage='P001',quote=self.brief.read_text(),task='review',acceptance='Editable drawings'),
                          dict(id='R2',passage='D002:P001',quote=self.rubric.read_text(),task='review',acceptance='Source-backed calculations')])
        self.plan=self.root/'plan.json'

    def save(self):
        self.plan.write_text(json.dumps(self.spec),encoding='utf-8')

    def test_intake_execute_diagnose_and_review_preserve_both_sources(self):
        result=intake(self.brief,self.root/'intake.json',supplements=[self.rubric])
        self.assertEqual([p['id'] for p in result['passages']],['P001','D002:P001'])
        self.assertEqual(result['supplemental_briefs'],self.spec['supplemental_briefs'])
        self.save()
        run=self.root/'run'
        result=execute(self.plan,run)
        self.assertIn(str(self.rubric.resolve()),result['inputs'])
        locator=result['requirements'][1]['source_locator']
        self.assertEqual(locator['source_document'],'rubric.md')
        self.assertEqual(locator['source_sha256'],digest(self.rubric))
        self.assertFalse(diagnose(self.plan,run)['execution_pass'])
        review=self.root/'review.json'
        self.assertEqual(len(template(self.plan,run,review)['requirements']),2)
        audit=assess(self.plan,run,review)
        self.assertTrue(audit['source_integrity_pass'])
        self.assertFalse(audit['design_accepted'])
        self.rubric.write_text('Changed performance requirement.',encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'brief hash differs'):
            diagnose(self.plan,run)

    def test_omitted_annex_passages_and_duplicate_documents_rejected(self):
        del self.spec['passage_dispositions']['D002:P001']
        self.save()
        with self.assertRaisesRegex(ProjectError,'every brief passage'):validate_plan(self.plan)
        self.spec['supplemental_briefs'][0]=dict(brief='brief.md',brief_sha256=digest(self.brief))
        with self.assertRaisesRegex(ProjectError,'duplicate brief'):plan_documents(self.root,self.spec)

    def test_delivery_distinguishes_identical_quotes_and_rejects_forged_locator(self):
        from bsa.delivery import run as audit_run
        quote='Include an editable <MEP> model.'
        self.brief.write_text(quote,encoding='utf-8')
        self.rubric.write_text(quote,encoding='utf-8')
        self.spec['brief_sha256']=digest(self.brief)
        self.spec['supplemental_briefs'][0]['brief_sha256']=digest(self.rubric)
        for requirement in self.spec['requirements']:requirement['quote']=quote
        self.save()
        run=self.root/'run';execute(self.plan,run)
        review=self.root/'review.json';template(self.plan,run,review)
        audit=audit_run(self.plan,run,review,self.root/'audit')
        rows=audit['requirements']
        self.assertEqual([r['source_locator']['source_document'] for r in rows],['brief.md','rubric.md'])
        self.assertEqual([r['passage'] for r in rows],['P001','D002:P001'])
        page=(self.root/'audit/report.html').read_text(encoding='utf-8')
        self.assertIn('brief.md',page);self.assertIn('rubric.md',page)
        self.assertIn('&lt;MEP&gt;',page);self.assertNotIn('<MEP>',page)
        self.assertIn('Acceptance target',page)
        self.assertIn('Source-backed calculations',page)
        self.assertFalse(audit['design_accepted'])
        report_path=run/'workflow.json'
        report=json.loads(report_path.read_text(encoding='utf-8'))
        report['requirements'][1]['source_locator']['source_document']='brief.md'
        report_path.write_text(json.dumps(report),encoding='utf-8')
        altered=assess(self.plan,run,review)
        self.assertEqual(altered['status'],'failed')
        self.assertTrue(any('locator differs' in issue for issue in altered['issues']))

    def test_empty_annex_blocks_planning_and_source_is_not_overwritten(self):
        self.rubric.write_text('',encoding='utf-8')
        self.spec['supplemental_briefs'][0]['brief_sha256']=digest(self.rubric)
        self.save()
        result=intake(self.brief,self.root/'intake.json',supplements=[self.rubric])
        self.assertEqual(result['coverage_status'],'blocked')
        issue=next(i for i in result['issues'] if i['severity']=='blocking')
        self.assertEqual(issue['id'],'D002:I001')
        self.assertEqual(issue['locator']['source_document'],'rubric.md')
        with self.assertRaisesRegex(ProjectError,'extraction blocked'):validate_plan(self.plan)
        with self.assertRaises(ProjectError):intake(self.brief,self.rubric,supplements=[self.rubric])
        self.assertEqual(self.rubric.read_text(),'')

    def test_escaping_or_malformed_supplement_rejected(self):
        for spec in ('rubric.md',{'brief':'../outside.md','brief_sha256':'0'*64},
                     {'brief':'rubric.md','brief_sha256':digest(self.rubric),'command':'anything'}):
            self.spec['supplemental_briefs']=[spec]
            with self.assertRaises(ProjectError):plan_documents(self.root,self.spec)

    def test_word_supplement_review_gate_is_independent_of_primary_text(self):
        annex=self.root/'annex.docx'
        with zipfile.ZipFile(annex,'w') as archive:
            archive.writestr('word/document.xml',
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>Keep the native editable model.</w:t></w:r></w:p></w:body></w:document>')
        self.spec['supplemental_briefs']=[dict(brief=annex.name,brief_sha256=digest(annex))]
        doc=plan_documents(self.root,self.spec)
        self.assertEqual(doc['issues'][0]['id'],'D002:I001')
        self.assertEqual(doc['issues'][0]['locator']['source_document'],annex.name)
        self.spec['requirements'][1]['quote']='Keep the native editable model.'
        self.save()
        with self.assertRaisesRegex(ProjectError,'each extraction issue'):validate_plan(self.plan)
        self.spec['document_review']={i['id']:'Synthetic XML fixture only; no actual Word layout acceptance' for i in doc['issues']}
        self.save()
        validate_plan(self.plan)

    @unittest.skipUnless(importlib.util.find_spec('pypdf'),'optional PDF dependency')
    def test_supplementary_ocr_retains_page_and_image_integrity(self):
        from pypdf import PdfWriter
        annex=self.root/'scan.pdf'
        writer=PdfWriter();writer.add_blank_page(width=200,height=200);writer.write(annex)
        image=self.root/'page.png';image.write_bytes(b'Synthetic raster identity; not actual OCR')
        sidecar=self.root/'ocr.json'
        sidecar.write_text(json.dumps(dict(version=1,source_sha256=digest(annex),pages=[
            dict(page=1,image=image.name,image_sha256=digest(image),lines=[
                dict(text='Include performance calculations and source references.',confidence=0.8,
                     box=[[0,0],[100,0],[100,20],[0,20]])])])),encoding='utf-8')
        self.spec['supplemental_briefs']=[dict(brief=annex.name,brief_sha256=digest(annex),
            ocr=sidecar.name,ocr_sha256=digest(sidecar))]
        doc=plan_documents(self.root,self.spec)
        self.spec['document_review']={i['id']:'Synthetic sidecar fixture; OCR correctness not verified' for i in doc['issues']}
        self.save()
        result=execute(self.plan,self.root/'run')
        self.assertIn(str(image.resolve()),result['inputs'])
        self.assertIn(str(sidecar.resolve()),result['inputs'])
        locator=result['requirements'][1]['source_locator']
        self.assertEqual(locator['source_document'],'scan.pdf')
        self.assertEqual(locator['page'],1)
        image.write_bytes(b'changed')
        with self.assertRaises(ProjectError):diagnose(self.plan,self.root/'run')


if __name__=='__main__':unittest.main()
