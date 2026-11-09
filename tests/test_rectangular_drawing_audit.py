from pathlib import Path
import tempfile
import unittest
import ezdxf
from bsa.bim import run as author
from bsa.rectangular_drawing import run
from bsa.rectangular_drawing_audit import audit
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'


class RectangularDrawingAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        author(EX/'straight-wall.json',cls.root/'model')
        cls.checked=run(cls.root/'model/model.ifc',EX/'straight-wall.json',EX/'drawing-settings.json',cls.root/'drawing')

    def check(self,path):return audit(path,self.checked['elements'],self.checked['axes'],self.checked['annotation_height_m'])

    def mutated(self,change):
        path=self.root/(self._testMethodName+'.dxf');doc=ezdxf.readfile(self.root/'drawing/segments.dxf');change(doc);doc.saveas(path)
        with self.assertRaises(ProjectError):self.check(path)

    def test_actual_positive_saved_source_audit(self):
        self.assertTrue(self.check(self.root/'drawing/segments.dxf')['saved_geometry_notes_identity_pass'])

    def test_changed_geometry_rejected(self):
        self.mutated(lambda d:next(iter(d.modelspace().query('LINE'))).dxf.__setattr__('end',(2.9,1.251,0)))

    def test_false_size_note_rejected(self):
        self.mutated(lambda d:next(iter(d.modelspace().query('TEXT'))).dxf.__setattr__('text','DUCT 100x100 mm INSIDE; L 2 m'))

    def test_missing_outline_rejected(self):
        self.mutated(lambda d:d.modelspace().delete_entity(next(iter(d.modelspace().query('LINE[layer=="BSA_DUCT_OUTLINE"]')))))

    def test_wrong_ifc_identity_rejected(self):
        self.mutated(lambda d:next(iter(d.modelspace())).set_xdata('BSA_IFC',[(1000,'unrelated')]))

    def test_hidden_and_nonplotting_rejected(self):
        for change in (lambda d:d.layers.get('BSA_DUCT_OUTLINE').off(),lambda d:d.layers.get('BSA_DUCT_OUTLINE').freeze(),
            lambda d:d.layers.get('BSA_DUCT_OUTLINE').dxf.__setattr__('plot',0),lambda d:next(iter(d.modelspace())).dxf.__setattr__('invisible',1)):
            self.mutated(change)

    def test_raw_paper_marker_cannot_be_normalized_away(self):
        path=self.root/'raw-paper.dxf';text=(self.root/'drawing/segments.dxf').read_text()
        self.assertIn('\nLINE\n',text);path.write_text(text.replace('\nLINE\n','\nLINE\n 67\n1\n',1))
        with self.assertRaises(ProjectError):self.check(path)
