import json
import math
import tempfile
import unittest
from pathlib import Path
import ezdxf
from bsa.bim import run as author
from bsa.rectangular_drawing import run
from bsa.rectangular_drawing_audit import audit
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/rectangular-air'

class RectangularElbowDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        author(EX/'elbow-chain-model.json',cls.root/'model')
        cls.checked=run(cls.root/'model/model.ifc',EX/'elbow-chain-model.json',EX/'drawing-settings.json',cls.root/'drawing')

    def check(self,path):
        r=self.checked
        return audit(path,r['elements'],r['axes'],r['annotation_height_m'])

    def mutation(self,change):
        d=ezdxf.readfile(self.root/'drawing/segments.dxf')
        change(d)
        path=self.root/(self._testMethodName+'.dxf')
        d.saveas(path)
        with self.assertRaises(ProjectError):self.check(path)

    def test_actual_arc_and_length(self):
        d=ezdxf.readfile(self.root/'drawing/segments.dxf')
        self.assertEqual(len(d.modelspace()),18)
        self.assertEqual(len(d.modelspace().query('ARC')),3)
        axis=next(iter(d.modelspace().query('ARC[layer=="BSA_PIPE_AXIS"]')))
        self.assertAlmostEqual(axis.dxf.radius,.8)
        bend=next(r for r in self.checked['elements'] if r['name']=='BEND')
        self.assertAlmostEqual(bend['length_m'],math.pi*.8/2)
        self.assertTrue(self.check(self.root/'drawing/segments.dxf')['saved_geometry_notes_identity_pass'])

    def test_chord_substitution_rejected(self):
        def change(d):
            a=next(iter(d.modelspace().query('ARC')))
            line=d.modelspace().add_line(a.start_point,a.end_point,dxfattribs={'layer':a.dxf.layer})
            line.set_xdata('BSA_IFC',a.get_xdata('BSA_IFC'))
            d.modelspace().delete_entity(a)
        self.mutation(change)

    def test_wrong_radius_rejected(self):
        self.mutation(lambda d:next(iter(d.modelspace().query('ARC'))).dxf.__setattr__('radius',.81))

    def test_hidden_arc_rejected(self):
        self.mutation(lambda d:next(iter(d.modelspace().query('ARC'))).dxf.__setattr__('invisible',1))

    def test_false_arc_length_rejected(self):
        def change(d):
            t=next(t for t in d.modelspace().query('TEXT') if 'ARC L' in t.dxf.text)
            t.dxf.text=t.dxf.text.replace('1.256637','1.131371')
        self.mutation(change)

    def test_non_bend_plane_rejected(self):
        s=json.loads((EX/'drawing-settings.json').read_text())
        s['axes']='XZ'
        path=self.root/'side.json';path.write_text(json.dumps(s))
        with self.assertRaises(ProjectError):
            run(self.root/'model/model.ifc',EX/'elbow-chain-model.json',path,self.root/'side')
        self.assertFalse((self.root/'side').exists())

