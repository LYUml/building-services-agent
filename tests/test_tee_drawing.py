from pathlib import Path
import tempfile
import unittest
import ifcopenshell
import ezdxf
from bsa.tee_assembly import run as assemble
from bsa.tee_drawing import run,verify_labels
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
            points=[p for e in doc.modelspace().query('LINE[layer!="BSA_CALLOUT"]') for p in (e.dxf.start,e.dxf.end)]
            self.assertAlmostEqual(min(p.x for p in points),-.02);self.assertAlmostEqual(max(p.x for p in points),.3)
            self.assertAlmostEqual(min(p.y for p in points),-.3);self.assertAlmostEqual(max(p.y for p in points),.3)
            self.assertEqual({row['callout'] for row in report['rows']},{'T1','P1','P2','P3'})
            self.assertTrue(verify_labels(doc,report['labels']))
            ent=doc.entitydb[report['labels'][0]['handle']];ent.dxf.text='WRONG'
            altered=root/'wrong-label.dxf';doc.saveas(altered)
            with self.assertRaisesRegex(ValueError,'content'):verify_labels(ezdxf.readfile(altered),report['labels'])
            for mode in ('hidden','identity'):
                d=ezdxf.readfile(root/'drawing/segments.dxf');e=d.entitydb[report['labels'][0]['handle']]
                if mode=='hidden':e.dxf.invisible=1
                else:e.set_xdata('BSA_IFC',[(1000,'wrong-guid')])
                target=root/(mode+'.dxf');d.saveas(target)
                with self.assertRaises(ValueError):verify_labels(ezdxf.readfile(target),report['labels'])
            f=ifcopenshell.open(str(model));f.by_type('IfcPipeSegment')[0].Representation.Representations[0].Items[0].Depth+=.02
            changed=root/'changed.ifc';f.write(str(changed))
            with self.assertRaisesRegex(ValueError,'verification failed'):run(changed,spec,assembly,root/'bad')
            self.assertFalse((root/'bad').exists())
if __name__=='__main__':unittest.main()
