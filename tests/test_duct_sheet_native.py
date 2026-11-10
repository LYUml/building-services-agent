import tempfile,unittest
from pathlib import Path
import ezdxf
from bsa.duct_sheet_native import compare
class NativeDuctSheetTests(unittest.TestCase):
 def test_effective_defaults_vertices_and_text_mutation(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);d=ezdxf.new();d.units=4;m=d.modelspace()
   p=m.add_lwpolyline([(0,0),(1,0),(1,1)],dxfattribs={'layer':'D','const_width':0})
   text=m.add_text('S',dxfattribs={'layer':'D'})
   a=root/'a.dxf';b=root/'b.dxf';d.saveas(a)
   p.dxf.discard('const_width');d.saveas(b);self.assertEqual(compare(a,b,['D'])['generated_entity_count'],2)
   p.set_points([(0,0),(2,0),(1,1)]);d.saveas(b)
   with self.assertRaisesRegex(ValueError,'vertices'):compare(a,b,['D'])
   p.set_points([(0,0),(1,0),(1,1)]);text.dxf.text='wrong';d.saveas(b)
   with self.assertRaisesRegex(ValueError,'attributes'):compare(a,b,['D'])
   with self.assertRaisesRegex(ValueError,'Every reviewed layer'):compare(a,b,['absent'])
