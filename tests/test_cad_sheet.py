import json
from pathlib import Path
import tempfile
import unittest
from bsa.cad_sheet import pdf_lines,plot
from bsa.engine import ProjectError
from test_cad_overlay import inputs


class CADSheetTests(unittest.TestCase):
    def test_pdf_ctm_stack_and_nonpainted_clip_path(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject,NameObject
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.pdf';writer=PdfWriter();page=writer.add_blank_page(width=297*72/25.4,height=210*72/25.4)
            stream=DecodedStreamObject()
            stream.set_data(b'2 0 0 2 0 0 cm q 1 0 0 1 10 20 cm 0 0 m 100 0 l W n 0 0 m 10 0 l S Q 0 0 m 5 0 l S')
            page[NameObject('/Contents')]=writer._add_object(stream)
            with path.open('wb') as f:writer.write(f)
            paper,lines=pdf_lines(path)
            self.assertAlmostEqual(paper[0],297,delta=1e-6);self.assertEqual(len(lines),2)
            self.assertAlmostEqual(lines[0][0][0],20*25.4/72)
            self.assertAlmostEqual(lines[0][1][0],40*25.4/72)
            self.assertAlmostEqual(lines[1][1][0],10*25.4/72)

    def test_oversized_window_and_unsafe_scale_rejected_before_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,drawing,selection,_=inputs(root)
            sheet=dict(source='Synthetic settings test',window_drawing_units=[-1000,-2000,7000,5000],scale_denominator=1,
                       reference_handle=json.loads(selection.read_text())['unit_check']['handle'],pdf_tolerance_mm=.2)
            with self.assertRaises(ProjectError):plot(root/'missing.dwg',drawing,sheet,root/'out.pdf',root/'missing.exe')
            sheet['scale_denominator']=0
            with self.assertRaises(ProjectError):plot(root/'missing.dwg',drawing,sheet,root/'out.pdf',root/'missing.exe')
            self.assertFalse((root/'out.pdf').exists())


if __name__=='__main__':unittest.main()
