import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from bsa.cad_sheet import check_text_line_clearance,check_window_entities,pdf_lines,plot
from bsa.cli import digest
from bsa.duct_sheet_native import run as publish_native
from bsa.engine import ProjectError
from tests.test_cad_overlay import inputs


class CADSheetTests(unittest.TestCase):
    def test_selected_line_crossing_reports_handles(self):
        from bsa.cad_text_layout import text_box

        drawing = ezdxf.new()
        model = drawing.modelspace()
        label = model.add_text('VAV-11')
        x0, y0, x1, y1 = text_box(label)
        y = (y0 + y1) / 2
        line = model.add_line((x0 - 1, y), (x1 + 1, y), dxfattribs={'layer': 'FLEX'})
        selection = dict(text_handles=[label.dxf.handle], line_layers=['flex'])
        with self.assertRaisesRegex(ProjectError, f'TEXT {label.dxf.handle}.*LINE {line.dxf.handle}'):
            check_text_line_clearance(drawing, selection)
        label.translate(0, y1 - y0 + 1, 0)
        self.assertEqual(check_text_line_clearance(drawing, selection), dict(text_count=1, obstacle_line_count=1))

    def test_required_entity_bounds_reject_clipping_before_plot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.dxf'
            doc = ezdxf.new(units=6)
            reference = doc.modelspace().add_line((0, 0), (1, 0))
            annotation = doc.modelspace().add_text('Required source note', dxfattribs={'insert': (1.9, 0.5), 'height': 0.1})
            handle = annotation.dxf.handle
            paper_entity = doc.layout().add_line((0, 0), (1, 0))
            doc.saveas(source)
            sheet = dict(source='Synthetic window coverage', window_drawing_units=[-1, -1, 2, 1],
                         scale_denominator=50, reference_handle=reference.dxf.handle,
                         pdf_tolerance_mm=.2, required_window_handles=[handle])
            with patch('bsa.cad_sheet.execute') as execute:
                with self.assertRaisesRegex(ProjectError, f'TEXT handle {handle} exceed the plot window'):
                    plot(root/'model.dwg', source, sheet, root/'out.pdf', root/'acad.exe')
                execute.assert_not_called()
            self.assertFalse((root/'out.pdf').exists())
            engine = root/'acad.exe'
            engine.touch()
            settings = root/'native.json'
            settings.write_text(json.dumps(dict(source_sha256=digest(source), layers=['0'], sheet=sheet)),
                                encoding='utf-8')
            with patch('bsa.duct_sheet_native.execute') as execute:
                with self.assertRaisesRegex(ProjectError, f'TEXT handle {handle} exceed the plot window'):
                    publish_native(source, settings, root/'native', engine)
                execute.assert_not_called()
            self.assertFalse((root/'native').exists())
            check_window_entities(doc, [handle.lower()], [-1, -1, 5, 1])
            with self.assertRaisesRegex(ProjectError, 'distinct modelspace entity handles'):
                check_window_entities(doc, [handle, handle.lower()], [-1, -1, 5, 1])
            with self.assertRaisesRegex(ProjectError, 'supported modelspace entity'):
                check_window_entities(doc, [paper_entity.dxf.handle], [-1, -1, 5, 1])

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
