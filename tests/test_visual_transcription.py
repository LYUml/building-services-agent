import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa import source_page,visual_transcription,source_review
from bsa.documents import extract
from bsa.workflow import validate_plan
from bsa.engineering_handoff import template
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('pdftoppm'),'requires host Poppler')
class VisualTranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.pdf';self.sidecar=self.root/'visual.json';self.plan=self.root/'plan.json'
        shutil.copyfile(ROOT/'docs/evidence/document-intake/source.pdf',self.source)
        source_page.run(self.source,1,self.root/'page',renderer=shutil.which('pdftoppm'))
        self.pages=[dict(page=1,receipt='page/page.json',lines=[dict(text='L1 / LGT-1',box=[[240,660],[650,660],[650,760],[240,760]])])]

    def prepare(self,pages=None):return visual_transcription.prepare(self.source,self.pages if pages is None else pages,self.sidecar,self.plan)

    def test_explicit_notes_preserve_source_quotes_gaps_and_do_not_execute(self):
        before=digest(self.source);result=self.prepare();self.assertEqual(result['status'],'needs_source_review')
        doc=extract(self.source,self.sidecar)
        self.assertEqual(doc['passages'][0]['text'],'L1 / LGT-1');self.assertNotIn('confidence',doc['passages'][0])
        with self.assertRaises(ValueError):validate_plan(self.plan)
        with self.assertRaises(ValueError):source_review.run(self.plan,{},self.root/'bad-review.json')
        self.assertFalse((self.root/'bad-review.json').exists())
        notes={i['id']:'Actual page inspected; literal source label checked, physical scale/meaning not established.' for i in doc['issues']}
        out=self.root/'reviewed.json';source_review.run(self.plan,notes,out);reviewed,_=validate_plan(out)
        original=json.loads(self.plan.read_text())
        for key in ('tasks','requirements','unresolved_inputs'):self.assertEqual(original[key],reviewed[key])
        self.assertIn(self.plan.name,reviewed['planning_records'])
        self.assertFalse(template(out,self.root/'interpretation.json')['executable']);self.assertEqual(digest(self.source),before)
        from bsa import modules
        request=dict(schema='bsa.module-request/1',project_id='visual-source-study',scenario_id='explicit-transcription',capability='requirements.source-inventory',
            coordinate_frame=dict(id='source-no-geometry',kind='source-world-si',length_unit='m',georeferenced=False),
            sources=dict(plan=dict(path='reviewed.json',sha256=digest(out))))
        path=self.root/'request.json';path.write_text(json.dumps(request))
        result=modules.run(path,'bsa.source-requirements',self.root/'requirements')
        self.assertEqual(result['execution']['status'],'completed')
        verified=modules.verify_result(self.root/'requirements/result.json')
        self.assertEqual(verified['payload']['passages'][0]['locator']['transcription_method'],'host_visual_transcription')
        self.assertEqual(verified['payload']['unresolved_inputs'],original['unresolved_inputs'])
        renderer_path=str(Path(shutil.which('pdftoppm')).resolve())
        self.assertNotIn(renderer_path,verified['inputs'])
        def changed_runtime(path):return '0'*64 if str(Path(path).resolve())==renderer_path else digest(Path(path))
        with patch('bsa.visual_transcription.digest',side_effect=changed_runtime):
            with self.assertRaisesRegex(ValueError,'renderer evidence changed'):modules.verify_result(self.root/'requirements/result.json')
        modules.verify_result(self.root/'requirements/result.json')

    def test_missing_page_confidence_and_invalid_pixel_region_reject_before_files(self):
        alternatives=[[],copy.deepcopy(self.pages),copy.deepcopy(self.pages)]
        alternatives[1][0]['lines'][0]['confidence']=1
        alternatives[2][0]['lines'][0]['box'][0][0]=-1
        for pages in alternatives:
            with self.assertRaises(ValueError):self.prepare(pages)
            self.assertFalse(self.sidecar.exists());self.assertFalse(self.plan.exists())

    def test_changed_image_or_source_receipt_cannot_create_transcription(self):
        image=self.root/'page/page.png';before=image.read_bytes();image.write_bytes(before+b'changed')
        with self.assertRaisesRegex(ValueError,'image changed'):self.prepare()
        image.write_bytes(before)
        p=self.root/'page/page.json';data=json.loads(p.read_text());data['source_sha256']='0'*64;p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Source-matching'):self.prepare()
        self.assertFalse(self.sidecar.exists())

    def test_transcription_tampering_invalidates_reviewed_source_plan(self):
        self.prepare();doc=extract(self.source,self.sidecar)
        source_review.run(self.plan,{i['id']:'Actual source inspected; engineering interpretation pending.' for i in doc['issues']},self.root/'reviewed.json')
        data=json.loads(self.sidecar.read_text());data['pages'][0]['lines'][0]['text']='Forged different label';self.sidecar.write_text(json.dumps(data))
        with self.assertRaises(ValueError):validate_plan(self.root/'reviewed.json')

    def test_concurrent_candidate_is_never_removed_on_exclusive_creation_failure(self):
        self.prepare();doc=extract(self.source,self.sidecar);out=self.root/'reviewed.json';candidate=out.with_name(out.name+'.candidate')
        original_open=Path.open
        def raced_open(path,*args,**kwargs):
            if path==candidate and args and args[0]=='x':
                with original_open(path,'w',encoding='utf-8') as stream:stream.write('Unrelated concurrent source')
                raise FileExistsError('Explicit concurrent creation control')
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',raced_open):
            with self.assertRaises(FileExistsError):source_review.run(self.plan,{i['id']:'Actual source inspected.' for i in doc['issues']},out)
        self.assertEqual(candidate.read_text(),'Unrelated concurrent source');self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
