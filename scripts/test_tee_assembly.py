import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from probe_tee_assembly import run,verify

ROOT=Path(__file__).resolve().parents[1]


class TeeAssemblyTests(unittest.TestCase):
    def test_penetration_and_gap_with_unchanged_ports(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            result=run(ROOT/'examples/tee-trial/spec.json',ROOT/'examples/tee-trial/assembly.json',root/'positive')
            self.assertTrue(result['assembly_checks_pass'])
            spec=json.loads((ROOT/'examples/tee-trial/spec.json').read_text(encoding='utf-8-sig'))
            lengths=json.loads((ROOT/'examples/tee-trial/assembly.json').read_text(encoding='utf-8-sig'))['pipe_lengths_m']
            for offset,label in [(-.01,'penetration'),(.01,'gap')]:
                f=ifcopenshell.open(str(root/'positive/assembly.ifc'))
                pipe=next(p for p in f.by_type('IfcPipeSegment') if p.Name=='branch')
                point=pipe.Representation.Representations[0].Items[0].Position.Location
                xyz=list(point.Coordinates);xyz[0]+=offset;point.Coordinates=xyz
                path=root/(label+'.ifc');f.write(str(path))
                report=verify(path,spec,lengths)
                self.assertTrue(report['checks']['connections_match'])
                self.assertFalse(report['checks']['pipe_geometry_ports_match'])
                self.assertFalse(report['assembly_checks_pass'])
                self.assertEqual(report['checks']['no_material_interpenetration'],label=='gap')


if __name__=='__main__':unittest.main()
