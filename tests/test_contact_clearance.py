import copy
import importlib.util
import json
from pathlib import Path
import unittest

from bsa.clash import inspect, validate_policy
from bsa.engine import ProjectError

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('manifold3d') and importlib.util.find_spec('ifcopenshell'), 'requires clash runtimes')
class OutsideRegionTests(unittest.TestCase):
    def policy(self, radius):
        policy = json.loads((ROOT/'examples/clash-policy.json').read_text())
        policy.update(contact_clearance_mode='outside_regions', contact_region_segments=64)
        for row in policy['allowed_contacts']:
            row['region_radius_m'] = radius
        return policy

    def test_saved_circular_model_small_region_fails_larger_explicit_region_passes(self):
        path = ROOT/'docs/evidence/circular-network/selected.ifc'
        before = path.read_bytes()
        small = inspect(path, self.policy(.15))
        self.assertFalse(small['calculated_checks_pass'])
        self.assertTrue(small['outside_region_checks'])
        self.assertTrue(any(not row['pass_check'] for row in small['outside_region_checks']))
        large = inspect(path, self.policy(.18))
        self.assertTrue(large['calculated_checks_pass'])
        self.assertEqual(len(large['outside_region_checks']), 2)
        for row in large['outside_region_checks']:
            self.assertEqual(len(row['directions']), 2)
            self.assertTrue(all(d['pass_check'] for d in row['directions']))
            self.assertTrue(all(r['mask_max_vertex_radius_m'] < r['sourced_radius_m'] for r in row['regions']))
        self.assertEqual(path.read_bytes(), before)

    def test_secondary_close_zone_is_not_hidden_by_intended_contact(self):
        import manifold3d as m
        from bsa.contact_clearance import prove
        a = m.Manifold.cube((1, 1, 1))
        b = m.Manifold.cube((1, 1, 1)).translate((1, 0, 0))
        contacts = [dict(centre_world_m=[1, .5, .5], region_radius_m=.8)]
        def mesh(solid):
            value = solid.to_mesh64()
            return value.vert_properties[:, :3].flatten().tolist(), value.tri_verts.flatten().tolist()
        ordinary = prove(('A', 'B'), {'A': mesh(a), 'B': mesh(b)}, contacts, .05, 64)
        self.assertTrue(ordinary['pass_check'])
        # Connected return arm approaches A by 20 mm away from the intended joint.
        arm = m.Manifold.cube((1.8, .2, .4)).translate((.2, 1.02, .3))
        bridge = m.Manifold.cube((.2, .42, .4)).translate((1.8, .8, .3))
        compound = m.Manifold.batch_boolean([b, arm, bridge], m.OpType.Add)
        result = prove(('A', 'B'), {'A': mesh(a), 'B': mesh(compound)}, contacts, .05, 64)
        self.assertEqual(result['status'], 'not_proven')
        self.assertFalse(result['pass_check'])
        self.assertTrue(any(d['conservative_gap_lower_bound_m'] < .021 for d in result['directions']))

    def test_mask_settings_are_explicit_and_bounded(self):
        for mutate in (lambda p:p.pop('contact_region_segments'),
                       lambda p:p.update(contact_region_segments=18),
                       lambda p:p.update(contact_region_segments=True),
                       lambda p:p.update(contact_clearance_mode='ignore_everything'),
                       lambda p:p['allowed_contacts'][0].update(region_radius_m=.00001)):
            p = copy.deepcopy(self.policy(.18)); mutate(p)
            with self.assertRaises(ProjectError): validate_policy(p)


if __name__ == '__main__':
    unittest.main()
