import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from bsa import source_page
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class SourcePageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.pdf';self.out=self.root/'page'
        shutil.copyfile(ROOT/'docs/evidence/document-intake/source.pdf',self.source)
        self.renderer=shutil.which('pdftoppm')

    @unittest.skipUnless(shutil.which('pdftoppm'),'requires host Poppler')
    def test_shared_renderer_retains_existing_ocr_dpi_behavior(self):
        from PIL import Image
        from pypdf import PdfReader
        from bsa.ocr import render_pdf_page
        image=render_pdf_page(self.source,self.root/'legacy-page',self.renderer,1)
        box=PdfReader(self.source).pages[0].mediabox
        with Image.open(image) as result:
            self.assertAlmostEqual(result.width,float(box.width)*180/72,delta=1)
            self.assertAlmostEqual(result.height,float(box.height)*180/72,delta=1)

    @unittest.skipUnless(shutil.which('pdftoppm'),'requires host Poppler')
    def test_actual_page_retains_source_and_does_not_clear_visual_review(self):
        from PIL import Image,ImageStat
        before=digest(self.source);result=source_page.run(self.source,1,self.out,renderer=self.renderer)
        self.assertEqual(digest(self.source),before);self.assertEqual(result['source_sha256'],before)
        self.assertFalse(result['extraction_review_cleared']);self.assertFalse(result['design_accepted'])
        self.assertEqual(result['image_sha256'],digest(self.out/'page.png'))
        self.assertEqual(json.loads((self.out/'page.json').read_text()),result)
        with Image.open(self.out/'page.png') as image:
            self.assertLessEqual(max(image.size),2048);self.assertGreater(max(ImageStat.Stat(image).stddev),0)
        with self.assertRaisesRegex(ValueError,'Fresh'):source_page.run(self.source,1,self.out,renderer=self.renderer)

    def test_missing_runtime_and_invalid_parameters_create_no_preview(self):
        for page,max_side in [(0,2048),(True,2048),(1,100000),(1,True)]:
            with self.assertRaises(ValueError):source_page.run(self.source,page,self.out,renderer=self.renderer,max_side=max_side)
        with self.assertRaisesRegex(ValueError,'runtime'):source_page.run(self.source,1,self.out)
        self.assertFalse(self.out.exists())

    @unittest.skipUnless(shutil.which('pdftoppm'),'requires host Poppler')
    def test_page_outside_pdf_rejects_before_renderer(self):
        with patch('bsa.source_page.render_pdf_page') as renderer:
            with self.assertRaisesRegex(ValueError,'page count'):source_page.run(self.source,2,self.out,renderer=self.renderer)
        renderer.assert_not_called();self.assertFalse(self.out.exists())

    @unittest.skipUnless(shutil.which('pdftoppm'),'requires host Poppler')
    def test_renderer_failure_retains_diagnostics_without_success_receipt(self):
        error=subprocess.CalledProcessError(1,['host-renderer'],stderr=b'Explicit synthetic renderer failure control')
        with patch('bsa.ocr.subprocess.run',side_effect=error):
            with self.assertRaisesRegex(ValueError,'renderer failed'):source_page.run(self.source,1,self.out,renderer=self.renderer)
        self.assertTrue((self.out/'page.renderer.log').exists());self.assertFalse((self.out/'page.json').exists())

    @unittest.skipUnless(shutil.which('pdftoppm'),'requires host Poppler')
    def test_mid_render_source_change_cannot_produce_a_success_receipt(self):
        render=source_page.render_pdf_page
        def mutate(*args,**kwargs):
            image=render(*args,**kwargs);self.source.write_bytes(self.source.read_bytes()+b'\n');return image
        with patch('bsa.source_page.render_pdf_page',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed during'):source_page.run(self.source,1,self.out,renderer=self.renderer)
        self.assertFalse((self.out/'page.json').exists())


if __name__=='__main__':unittest.main()
