import copy
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa import unequal_rectangular_tee as author
from bsa.rectangular_tee_profiles import sections,canonical_case

ROOT=Path(__file__).resolve().parents[1]


class TeeProfilesTests(unittest.TestCase):
    def test_native_rotated_profiles_and_negative_caps(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory)
            tee=json.loads((ROOT/'examples/rectangular-tee/project.json').read_text())
            tee['placement'].update(origin_m=[12,-7,4],rotation=[[0,0,1],[0,1,0],[-1,0,0]])
            source=root/'input.json';source.write_text(json.dumps(dict(tee=tee,branch_section_m=[.2,.15])))
            author.run(source,root/'model')
            model=ifcopenshell.open(str(root/'model/unequal-tee.ifc'));obj=model.by_type('IfcDuctFitting')[0]
            sizes=sections(obj);ports=author.base.system_util.get_ports(obj)
            self.assertEqual(sizes[next(p.GlobalId for p in ports if p.Name=='branch')],[.2,.15])
            case=dict(air=dict(density_kg_m3=1.2),port_flows={g:dict(owner_guid=obj.GlobalId,width_m=w,height_m=h,flow_m3_s=.1) for g,(w,h) in sizes.items()})
            original=copy.deepcopy(case);fresh=canonical_case(model,case,[obj.GlobalId]);self.assertEqual(case,original)
            for guid,(w,h) in sizes.items():self.assertAlmostEqual(fresh['port_flows'][guid]['actual_velocity_m_s'],.1/(w*h))
            bad=copy.deepcopy(case);bad['port_flows'][ports[0].GlobalId]['width_m']+=.01
            with self.assertRaises(ValueError):canonical_case(model,bad,[obj.GlobalId])
            with self.assertRaises(ValueError):canonical_case(model,case,[obj.GlobalId,obj.GlobalId])
            wall=obj.Representation.Representations[0].Items[0]
            wall.FirstOperand.SecondOperand.SweptArea.XDim+=.01
            with self.assertRaises(ValueError):sections(obj)
            wall.FirstOperand.SecondOperand.SweptArea.XDim-=.01
            ports[0].ObjectPlacement.RelativePlacement.Location.Coordinates=(8.,0.,0.)
            with self.assertRaises(ValueError):sections(obj)


if __name__=='__main__':unittest.main()
