import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.system as system
import ifcopenshell.util.placement as placement
from bsa import interface_contacts as tool,compound_junction
from tests import test_compound_junction as fixtures


class InterfaceContactsTests(unittest.TestCase):
    def test_all_five_native_caps_including_two_in_same_plane(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'runs') as folder:
            folder=Path(folder);data=fixtures.CompoundJunctionTests().fixture();source=folder/'project.json';source.write_text(json.dumps(data));compound_junction.run(source,folder/'native');file=ifcopenshell.open(str(folder/'native/junction.ifc'));obj=file.by_type('IfcDuctFitting')[0];settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);shape=ifcopenshell.geom.create_shape(settings,obj);v=np.array(shape.geometry.verts).reshape(-1,3);f=np.array(shape.geometry.faces).reshape(-1,3)
            caps={p.Name:tool.cap(v,f,placement.get_local_placement(p.ObjectPlacement)) for p in system.get_ports(obj)}
            self.assertEqual(len(caps),5);self.assertTrue(all(c['material_area_m2']>0 for c in caps.values()));self.assertAlmostEqual(caps['a']['inner_section_m'][0],.4)
            tool.matching(caps['a'],copy.deepcopy(caps['a']))
            changed=copy.deepcopy(caps['a']);changed['inner_corners'][0][0]+=.001
            with self.assertRaisesRegex(ValueError,'boundaries'):tool.matching(changed,caps['a'])

    def test_filled_cap_and_wrong_port_origin_reject(self):
        vertices=np.array([[-1,-1,0],[1,-1,0],[1,1,0],[-1,1,0.]])
        with self.assertRaisesRegex(ValueError,'outer and one inner'):tool.cap(vertices,[[0,1,2],[0,2,3]],np.eye(4))
        frame=np.eye(4);frame[0,3]=.1
        with self.assertRaisesRegex(ValueError,'centred'):tool.cap(vertices,[[0,1,2],[0,2,3]],frame)

    def test_outside_proof_identity_and_vacuity_cannot_be_hidden(self):
        study=dict(outside_region_checks=[dict(pair=['A','B'],pass_check=True,status='pass',directions=[dict(outside_guid='A',full_guid='B',outside_empty=False,conservative_gap_lower_bound_m=.00004,pass_check=True)])])
        changed=copy.deepcopy(study);changed['outside_region_checks'][0]['directions'][0]['outside_empty']=True
        self.assertNotEqual(tool.proof_signature(study),tool.proof_signature(changed))
        changed=copy.deepcopy(study);changed['outside_region_checks'][0]['directions'][0]['conservative_gap_lower_bound_m']=0
        self.assertNotEqual(tool.proof_signature(study),tool.proof_signature(changed))
        error=dict(outside_region_checks=[dict(pair=['A','B'],pass_check=False,status='error',reason='Native clipping failed')])
        self.assertFalse(tool.proof_signature(error)[0][1])


if __name__=='__main__':unittest.main()
