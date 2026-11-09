import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
import ezdxf
from bsa.bim import run as author
from bsa.rectangular_drawing import run
from bsa.workflow import validate_plan,execute
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'


class RectangularDrawingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def test_actual_saved_wall_dimensions_and_guid_linked_dxf(self):
        author(EX/'straight-wall.json',self.root/'model')
        r=run(self.root/'model/model.ifc',EX/'straight-wall.json',EX/'drawing-settings.json',self.root/'drawing')
        d=ezdxf.readfile(self.root/'drawing/segments.dxf')
        self.assertEqual(len(d.modelspace().query('LINE[layer=="BSA_PIPE_AXIS"]')),1)
        self.assertIn('500x300',next(iter(d.modelspace().query('TEXT'))).dxf.text)
        self.assertTrue(all(e.has_xdata('BSA_IFC') for e in d.modelspace()))
        self.assertTrue(r['complete_represented_coverage']);self.assertFalse(r['design_accepted'])

    def test_changed_native_section_rejected(self):
        author(EX/'straight-wall.json',self.root/'model');path=self.root/'model/model.ifc';m=ifcopenshell.open(str(path))
        m.by_type('IfcDuctSegment')[0].Representation.Representations[0].Items[0].SweptArea.XDim+=.01;m.write(str(path))
        with self.assertRaises(ProjectError):run(path,EX/'straight-wall.json',EX/'drawing-settings.json',self.root/'drawing')
        self.assertFalse((self.root/'drawing').exists())

    def test_end_on_view_rejected(self):
        author(EX/'straight-wall.json',self.root/'model');s=json.loads((EX/'drawing-settings.json').read_text());s['axes']='YZ'
        path=self.root/'settings.json';path.write_text(json.dumps(s))
        with self.assertRaisesRegex(ProjectError,'end-on'):run(self.root/'model/model.ifc',EX/'straight-wall.json',path,self.root/'drawing')

    def test_same_model_clash_gate_required(self):
        for name in EX.glob('*.json'):(self.root/name.name).write_bytes(name.read_bytes())
        (self.root/'brief.md').write_bytes((EX/'brief.md').read_bytes())
        path=self.root/'clearance-drawing-plan.json';p=json.loads(path.read_text());p['tasks'][2]['requires_pass']=[];path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'same-model clash'):validate_plan(path)

    def test_missing_autocad_leaves_drawing_unexecuted(self):
        out=self.root/'run';r=execute(EX/'clearance-drawing-plan.json',out)
        report=json.loads((out/'workflow.json').read_text())
        self.assertEqual(report['tasks']['drawing']['status'],'pending')
        self.assertIn('AutoCAD',report['tasks']['drawing']['scope']);self.assertFalse((out/'drawing').exists())
