import unittest
import ezdxf
from bsa.cad_sheet import reference_points
from bsa.engine import ProjectError

class NativeSpatialReferenceTests(unittest.TestCase):
    def test_explicit_straight_source_segment_and_curves_rejected(self):
        doc=ezdxf.new();poly=doc.modelspace().add_lwpolyline([(0,0),(4,0),(4,3)],close=True)
        a,b=reference_points(doc,dict(reference_handle=poly.dxf.handle,reference_segment_index=0));self.assertEqual(tuple(a),(0,0,0));self.assertEqual(tuple(b),(4,0,0))
        for index in (-1,3,True,None):
            with self.subTest(index=index),self.assertRaises(ProjectError):reference_points(doc,dict(reference_handle=poly.dxf.handle,reference_segment_index=index))
        poly.set_points([(0,0,0,0,1),(4,0,0,0,0),(4,3,0,0,0)])
        with self.assertRaises(ProjectError):reference_points(doc,dict(reference_handle=poly.dxf.handle,reference_segment_index=0))

    def test_native_point_location_comparison(self):
        import tempfile
        from pathlib import Path
        from bsa.duct_sheet_native import compare
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.dxf';b=Path(folder)/'b.dxf';doc=ezdxf.new();doc.modelspace().add_point((1,2,0),dxfattribs={'layer':'POINTS'});doc.saveas(a);doc.saveas(b)
            self.assertTrue(compare(a,b,['POINTS'])['generated_native_correspondence'])
            doc.modelspace()[0].dxf.location=(3,2,0);doc.saveas(b)
            with self.assertRaises(ValueError):compare(a,b,['POINTS'])
