import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from probe_tee_assembly import run,verify

ROOT=Path(__file__).resolve().parents[1]


class TeeAssemblyTests(unittest.TestCase):
    def test_identity_survives_revision_and_rejects_substitution(self):
        import ifcopenshell.util.system as system
        def inventory(path):
            f=ifcopenshell.open(str(path));result={}
            for obj in f.by_type('IfcPipeFitting')+f.by_type('IfcPipeSegment'):
                result[(obj.is_a(),obj.Name)]=obj.GlobalId
                for port in system.get_ports(obj):result[('port',obj.Name,port.Name)]=port.GlobalId
            return result
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            spec=json.loads((ROOT/'examples/tee-trial/spec.json').read_text(encoding='utf-8-sig'))
            assembly=json.loads((ROOT/'examples/tee-trial/assembly.json').read_text(encoding='utf-8-sig'))
            sp=root/'spec.json';ap=root/'assembly.json'
            sp.write_text(json.dumps(spec));ap.write_text(json.dumps(assembly))
            for name in ('first','repeat','revised','independent'):
                if name=='revised':
                    assembly['pipe_lengths_m']['branch']=.3;ap.write_text(json.dumps(assembly))
                if name=='independent':
                    spec['project_uuid']='6c0815b2-26eb-4c98-a854-e5c0601f24ad';sp.write_text(json.dumps(spec))
                self.assertTrue(run(sp,ap,root/name)['assembly_checks_pass'])
            first=inventory(root/'first/assembly.ifc')
            self.assertEqual(first,inventory(root/'repeat/assembly.ifc'))
            self.assertEqual(first,inventory(root/'revised/assembly.ifc'))
            self.assertTrue(set(first.values()).isdisjoint(inventory(root/'independent/assembly.ifc').values()))
            f=ifcopenshell.open(str(root/'independent/assembly.ifc'))
            f.by_type('IfcDistributionPort')[0].GlobalId=ifcopenshell.guid.new()
            path=root/'changed.ifc';f.write(str(path))
            report=verify(path,spec,assembly['pipe_lengths_m'])
            self.assertFalse(report['checks']['stable_identities'])
            self.assertFalse(report['assembly_checks_pass'])
            spec['project_uuid']='not-a-uuid';sp.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError,'canonical project_uuid'):run(sp,ap,root/'invalid')
            self.assertFalse((root/'invalid').exists())

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
