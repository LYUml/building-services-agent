"""Small binary/XML parser fixtures, not user-facing authored documents."""
import importlib.util
import os
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from bsa.documents import extract, check_review
from bsa.workflow import intake, validate_plan, execute
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
NS='http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def word_fixture(path, body, extras=None):
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="{NS}"><w:body>{body}</w:body></w:document>')
        for name,value in (extras or {}).items():z.writestr(name,value)


def pdf_fixture(path, texts):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter()
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    for text in texts:
        page=writer.add_blank_page(width=600,height=800)
        if text:
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            stream=DecodedStreamObject()
            stream.set_data(f'BT /F1 12 Tf 50 700 Td ({text}) Tj ET'.encode('ascii'))
            page[NameObject('/Contents')]=writer._add_object(stream)
        else:
            # Non-text graphic fixture: unlike a genuinely empty content stream.
            stream=DecodedStreamObject();stream.set_data(b'0 0 100 100 re f')
            page[NameObject('/Contents')]=writer._add_object(stream)
    writer.write(path)


class DocumentTests(unittest.TestCase):
    def test_true_trailing_blank_still_needs_visual_review(self):
        from pypdf import PdfReader,PdfWriter
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'text.pdf';pdf_fixture(source,['Source requirement'])
            writer=PdfWriter();writer.append(PdfReader(source));writer.add_blank_page(width=600,height=800)
            path=Path(folder)/'trailing.pdf';writer.write(path)
            doc=extract(path)
            self.assertTrue(any(i['code']=='blank_page' for i in doc['issues']))
            self.assertFalse(any(i['severity']=='blocking' for i in doc['issues']))
            with self.assertRaises(ProjectError):check_review(doc,{})
            check_review(doc,{i['id']:'Inspected synthetic page render: trailing page blank' for i in doc['issues']})
            writer=PdfWriter();writer.add_blank_page(width=600,height=800);empty=Path(folder)/'empty.pdf';writer.write(empty)
            self.assertEqual(extract(empty)['coverage_status'],'blocked')

    def test_nested_textbox_requirements_keep_independent_locators(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'brief.docx'
            word_fixture(path,
                '<w:p><w:r><w:t>Outer requirement.</w:t></w:r>'
                '<w:r><w:pict><w:txbxContent>'
                '<w:p><w:r><w:t>Pump requirement.</w:t></w:r>'
                '<w:r><w:pict><w:txbxContent><w:p><w:r><w:t>Tank requirement.</w:t>'
                '</w:r></w:p></w:txbxContent></w:pict></w:r></w:p>'
                '<w:p><w:r><w:t>Standby requirement.</w:t></w:r></w:p>'
                '</w:txbxContent></w:pict></w:r>'
                '<w:r><w:t> Outer continuation.</w:t></w:r></w:p>')
            before=digest(path)
            doc=extract(path)
            rows=doc['passages']
            self.assertEqual([r['text'] for r in rows],[
                'Outer requirement. Outer continuation.',
                'Pump requirement.','Tank requirement.','Standby requirement.'])
            self.assertEqual([r['block_index'] for r in rows],[1,2,3,4])
            self.assertEqual(len({r['xml_path'] for r in rows}),4)
            self.assertIn('/txbxContent[1]/p[1]',rows[1]['xml_path'])
            self.assertIn('/txbxContent[1]/p[2]',rows[3]['xml_path'])
            self.assertTrue(any(i['code']=='embedded_content' for i in doc['issues']))
            self.assertEqual(doc['coverage_status'],'needs review')
            self.assertEqual(digest(path),before)

            plan=dict(version=1,brief=path.name,brief_sha256=before,
                document_review={i['id']:'Parser fixture only; rendering is not verified' for i in doc['issues']},
                passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='review',kind='manual',description='Review full requirements')],
                requirements=[dict(id='R1',passage='P001',quote=rows[0]['text'],
                    task='review',acceptance='Independent source review')])
            plan_path=Path(folder)/'plan.json'
            plan_path.write_text(json.dumps(plan),encoding='utf-8')
            with self.assertRaisesRegex(ProjectError,'every brief passage'):
                validate_plan(plan_path)
            plan['passage_dispositions']={r['id']:'requirement' for r in rows}
            plan['requirements']=[dict(id='R'+str(i),passage=r['id'],quote=r['text'],
                task='review',acceptance='Review full source meaning') for i,r in enumerate(rows,1)]
            plan_path.write_text(json.dumps(plan),encoding='utf-8')
            result=execute(plan_path,Path(folder)/'run')
            self.assertEqual(len(result['requirements']),4)
            self.assertTrue(all(r['execution_status']=='pending' for r in result['requirements']))
            self.assertEqual(result['requirements'][1]['source_locator']['xml_path'],rows[1]['xml_path'])

    def test_word_table_header_and_note_locators(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'brief.docx'
            word_fixture(path,'<w:p><w:r><w:t>机电要求</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>MCB 6 A</w:t></w:r></w:p></w:tc></w:tr></w:tbl>',
                {'word/header1.xml':f'<w:hdr xmlns:w="{NS}"><w:p><w:r><w:t>Header note</w:t></w:r></w:p></w:hdr>',
                 'word/footnotes.xml':f'<w:footnotes xmlns:w="{NS}"><w:footnote><w:p><w:r><w:t>Footnote requirement</w:t></w:r></w:p></w:footnote></w:footnotes>'})
            before=digest(path);r=extract(path)
            self.assertEqual([p['text'] for p in r['passages']][:2],['机电要求','MCB 6 A'])
            self.assertIn('/tbl[1]/tr[1]/tc[1]/p[1]',r['passages'][1]['xml_path'])
            self.assertTrue(any(p['part']=='word/header1.xml' for p in r['passages']))
            self.assertTrue(any(p['part']=='word/footnotes.xml' for p in r['passages']))
            self.assertEqual(digest(path),before)
            with self.assertRaises(ProjectError):check_review(r,{})

    def test_word_tracked_changes_block_planning(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'brief.docx'
            word_fixture(path,'<w:p><w:del><w:r><w:delText>Old 10 A</w:delText></w:r></w:del><w:ins><w:r><w:t>New 6 A</w:t></w:r></w:ins></w:p>')
            r=extract(path)
            self.assertEqual(r['coverage_status'],'blocked')
            with self.assertRaises(ProjectError):check_review(r,{i['id']:'reviewed' for i in r['issues']})

    def test_word_requirement_can_drive_electrical_with_review_note(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);brief=root/'brief.docx'
            word_fixture(brief,'<w:p><w:r><w:t>Calculate and draw the three-light circuit.</w:t></w:r></w:p>')
            doc=extract(brief)
            (root/'project.json').write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
            plan=dict(version=1,brief='brief.docx',brief_sha256=digest(brief),
                document_review={i['id']:'Synthetic fixture contains one paragraph and no table, image, numbering or equation' for i in doc['issues']},
                passage_dispositions={'P001':'requirement'},tasks=[dict(id='electrical',kind='electrical',project='project.json')],
                requirements=[dict(id='R1',passage='P001',quote=doc['passages'][0]['text'],task='electrical',acceptance='conditional calculation and overlay')])
            path=root/'plan.json';path.write_text(json.dumps(plan),encoding='utf-8')
            r=execute(path,root/'run')
            self.assertTrue(r['execution_pass'])
            self.assertEqual(r['requirements'][0]['source_locator']['part'],'word/document.xml')
            self.assertFalse(r['design_accepted'])

    @unittest.skipUnless(importlib.util.find_spec('pypdf'),'optional PDF dependency')
    def test_pdf_page_locator_and_missing_text_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'brief.pdf'
            pdf_fixture(path,['Check circuit 6 A','Use 230 V supply'])
            r=intake(path,root/'intake.json')
            self.assertEqual([p['page'] for p in r['passages']],[1,2])
            self.assertEqual(r['passages'][1]['text'],'Use 230 V supply')
            with self.assertRaises(ProjectError):check_review(r,{})
            check_review(r,{i['id']:'Fixture page contains one unambiguous text line' for i in r['issues']})
            scan=root/'scan.pdf';pdf_fixture(scan,['One readable page',''])
            s=extract(scan)
            self.assertEqual(s['coverage_status'],'blocked')
            self.assertEqual(next(i for i in s['issues'] if i['code']=='no_text')['locator']['page'],2)
            with self.assertRaises(ProjectError):check_review(s,{i['id']:'acknowledged' for i in s['issues']})

    def test_empty_text_is_not_a_valid_covered_brief(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'empty.txt';path.write_text('  \n')
            r=extract(path)
            self.assertEqual(r['coverage_status'],'blocked')

    @unittest.skipUnless(importlib.util.find_spec('pypdf'),'optional PDF dependency')
    def test_ocr_source_and_image_hashes_and_review_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'scan.pdf';pdf_fixture(source,[''])
            image=root/'page.png';image.write_bytes(b'unit fixture raster bytes')
            data=dict(version=1,source_sha256=digest(source),pages=[dict(page=1,image='page.png',
                image_sha256=digest(image),lines=[dict(text='MCB 6 A',confidence=0.92,
                box=[[0,0],[100,0],[100,20],[0,20]])])])
            sidecar=root/'ocr.json';sidecar.write_text(json.dumps(data),encoding='utf-8')
            doc=extract(source,sidecar)
            self.assertEqual(doc['coverage_status'],'needs review')
            self.assertEqual(doc['passages'][0]['text'],'MCB 6 A')
            self.assertEqual(doc['passages'][0]['ocr_line'],1)
            elsewhere=root/'sources'
            elsewhere.mkdir()
            copied=elsewhere/'scan.pdf'
            copied.write_bytes(source.read_bytes())
            indexed=intake(copied,root/'external-ocr-intake.json',sidecar)
            self.assertEqual(indexed['passages'][0]['text'],'MCB 6 A')
            with self.assertRaises(ProjectError):check_review(doc,{})
            check_review(doc,{i['id']:'Source transcription explicitly reviewed' for i in doc['issues']})
            (root/'project.json').write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
            plan=dict(version=1,brief='scan.pdf',brief_sha256=digest(source),ocr='ocr.json',ocr_sha256=digest(sidecar),
                document_review={i['id']:'Synthetic transcription fixture reviewed' for i in doc['issues']},
                passage_dispositions={'P001':'requirement'},tasks=[dict(id='electrical',kind='electrical',project='project.json')],
                requirements=[dict(id='R1',passage='P001',quote='MCB 6 A',task='electrical',acceptance='conditional checks')])
            plan_path=root/'plan.json';plan_path.write_text(json.dumps(plan),encoding='utf-8')
            result=execute(plan_path,root/'run')
            self.assertIn(str(image.resolve()),result['inputs'])
            self.assertIn(str(sidecar.resolve()),result['inputs'])
            image.write_bytes(b'changed image')
            with self.assertRaises(ProjectError):extract(source,sidecar)
            data['source_sha256']='0'*64
            sidecar.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ProjectError):extract(source,sidecar)

    @unittest.skipUnless(os.environ.get('BSA_TEST_OCR_INPUT'),'requires explicit local OCR input')
    def test_real_offline_ocr_preserves_raw_lines(self):
        from bsa.ocr import run
        root=ROOT/'runs';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source=Path(os.environ['BSA_TEST_OCR_INPUT'])
            before=digest(source)
            result=run(source,Path(folder)/'ocr')
            self.assertTrue(result['model_sha256'])
            self.assertEqual(digest(source),before)
            self.assertGreaterEqual(sum(len(p['lines']) for p in result['pages']),3)
            doc=extract(source,Path(folder)/'ocr/ocr.json')
            self.assertEqual(doc['coverage_status'],'needs review')
            self.assertTrue(any('L1' in p['text'] for p in doc['passages']))


if __name__=='__main__':unittest.main()
