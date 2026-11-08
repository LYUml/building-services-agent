"""Saved finite elbow contact, bore and unwaivable material-overlap regressions."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

from bsa.clash import inspect

ROOT = Path(__file__).resolve().parents[1]
AVAILABLE = bool(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('manifold3d'))


@unittest.skipUnless(AVAILABLE, 'requires IFC and Manifold runtimes')
class ElbowClashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.root = Path(cls.folder.name)
        evidence = ROOT/'docs/evidence/circular-elbow'
        manifest = json.loads((evidence/'validation.json').read_text())
        with zipfile.ZipFile(evidence/'workflow.zip') as archive:
            data = archive.read('model/bim/model.ifc')
        assert hashlib.sha256(data).hexdigest() == manifest['archive_entries']['model/bim/model.ifc']
        cls.original = cls.root/'original.ifc'
        cls.original.write_bytes(data)
        cls.original_hash = hashlib.sha256(data).hexdigest()
        cls.policy = json.loads((ROOT/'examples/circular-elbow/clash-policy.json').read_text())

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(cls.original.read_bytes()).hexdigest() == cls.original_hash
        cls.folder.cleanup()

    def test_finite_contacts_and_both_outside_clearance_directions(self):
        result = inspect(self.original, self.policy)
        self.assertTrue(result['calculated_checks_pass'])
        self.assertEqual(result['physical_element_count'], 3)
        self.assertEqual(result['valid_geometry_count'], 3)
        self.assertEqual(len(result['accepted_contacts']), 2)
        self.assertEqual(len(result['outside_region_checks']), 2)
        for proof in result['outside_region_checks']:
            self.assertTrue(proof['pass_check'])
            self.assertEqual(len(proof['directions']), 2)
            self.assertTrue(all(row['pass_check'] and not row['outside_empty'] for row in proof['directions']))
        self.assertFalse(result['design_accepted'])

    def test_connected_ports_cannot_waive_straight_wall_intrusion_into_elbow(self):
        import ifcopenshell
        import ifcopenshell.util.placement as placement
        native = ifcopenshell.open(str(self.original))
        before = {p.GlobalId: placement.get_local_placement(p.ObjectPlacement).tolist()
                  for p in native.by_type('IfcDistributionPort')}
        incoming = next(p for p in native.by_type('IfcPipeSegment') if p.Name == 'IN')
        body = next(r for r in incoming.Representation.Representations if r.RepresentationIdentifier == 'Body')
        self.assertTrue(body.Items[0].is_a('IfcExtrudedAreaSolid'))
        body.Items[0].Depth += .02  # Only solid geometry changes; logical ports stay coincident.
        path = self.root/'intrusion.ifc'
        native.write(str(path))
        saved = ifcopenshell.open(str(path))
        after = {p.GlobalId: placement.get_local_placement(p.ObjectPlacement).tolist()
                 for p in saved.by_type('IfcDistributionPort')}
        self.assertEqual(before, after)
        result = inspect(path, self.policy)
        self.assertFalse(result['calculated_checks_pass'])
        hits = [r for r in result['intersections'] if r['type'] == 'manifold_mesh_overlap']
        self.assertTrue(any(set(r['names']) == {'IN', 'BEND'} and r['overlap_volume_m3'] > 1e-6 for r in hits))
        self.assertFalse(any(set(r['names']) == {'IN', 'BEND'} for r in result['accepted_contacts']))

    def sensor(self, z_offset, size, name):
        """Explicit synthetic cube placed at the arc midpoint, independent of body bounds."""
        import ifcopenshell
        import ifcopenshell.api as api
        import numpy as np
        native = ifcopenshell.open(str(self.original))
        obj = api.run('root.create_entity', native, ifc_class='IfcSensor', name=name)
        w = size
        vertices = [(0.,0.,0.),(w,0.,0.),(w,w,0.),(0.,w,0.),(0.,0.,w),(w,0.,w),(w,w,w),(0.,w,w)]
        faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        context = next(c for c in native.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier == 'Body')
        rep = api.run('geometry.add_mesh_representation', native, context=context, vertices=[vertices], faces=[faces])
        api.run('geometry.assign_representation', native, product=obj, representation=rep)
        matrix = np.eye(4)
        matrix[:3,3] = [2+.3/math.sqrt(2)-w/2, 2+.3/math.sqrt(2)-w/2, 1+z_offset-w/2]
        api.run('geometry.edit_object_placement', native, product=obj, matrix=matrix, is_si=True)
        api.run('spatial.assign_container', native, products=[obj], relating_structure=native.by_type('IfcSpace')[0])
        path = self.root/(name+'.ifc')
        native.write(str(path))
        return path

    def test_curved_bore_is_empty_despite_overlapping_bounds(self):
        result = inspect(self.sensor(0, .02, 'BORE_SENSOR'), self.policy)
        self.assertTrue(result['calculated_checks_pass'])
        self.assertEqual(result['valid_geometry_count'], 4)
        self.assertTrue(result['solid_pair_checks'])
        self.assertTrue(all(abs(row['mesh_common_volume_m3']) < 1e-10 for row in result['solid_pair_checks']))

    def test_mid_arc_wall_overlap_and_close_bore_obstacle_fail(self):
        overlap = inspect(self.sensor(.045, .02, 'WALL_SENSOR'), self.policy)
        self.assertFalse(overlap['calculated_checks_pass'])
        self.assertTrue(any(r['type'] == 'manifold_mesh_overlap' and 'WALL_SENSOR' in r['names'] for r in overlap['intersections']))
        close = inspect(self.sensor(.028, .01, 'CLOSE_SENSOR'), self.policy)
        self.assertFalse(close['calculated_checks_pass'])
        self.assertFalse(close['intersections'])
        self.assertTrue(any('CLOSE_SENSOR' in r['names'] for r in close['clearance_violations']))


if __name__ == '__main__':
    unittest.main()
