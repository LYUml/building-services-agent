from pathlib import Path
import tempfile
import unittest
import ifcopenshell
import ezdxf
from bsa.tee_assembly import run as assemble
from bsa.tee_drawing import run
ROOT=Path(__file__).resolve().parents[1]
class TeeDrawingTests(unittest.TestCase):
    def test_rotated_saved_geometry_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);source=ROOT/'examples/tee-trial';spec=source/'placed-spec.json';assembly=source/'assembly.json'
            assemble(spec,assembly,root/'model');model=root/'model/assembly.ifc'
            report=run(model,spec,assembly,root/'drawing');self.assertEqual(len(report['rows']),4)
            doc=ezdxf.readfile(root/'drawing/segments.dxf');axes=list(doc.modelspace().query('LINE[layer=="BSA_PIPE_AXIS"]'))
            self.assertEqual(len(axes),5)
            pipe_guids={r['guid'] for r in report['rows'] if r['kind']=='pipe'}
            for line in axes:
                if line.get_xdata('BSA_IFC')[0].value in pipe_guids:self.assertAlmostEqual(line.dxf.start.distance(line.dxf.end),.2)
            points=[p for e in doc.modelspace().query('LINE') for p in (e.dxf.start,e.dxf.end)]
            self.assertAlmostEqual(min(p.x for p in points),-.02);self.assertAlmostEqual(max(p.x for p in points),.3)
            self.assertAlmostEqual(min(p.y for p in points),-.3);self.assertAlmostEqual(max(p.y for p in points),.3)
            f=ifcopenshell.open(str(model));f.by_type('IfcPipeSegment')[0].Representation.Representations[0].Items[0].Depth+=.02
            changed=root/'changed.ifc';f.write(str(changed))
            with self.assertRaisesRegex(ValueError,'verification failed'):run(changed,spec,assembly,root/'bad')
            self.assertFalse((root/'bad').exists())
if __name__=='__main__':unittest.main()
