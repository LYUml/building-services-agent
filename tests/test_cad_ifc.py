import unittest
import numpy as np
import manifold3d
from bsa.cad_ifc import mass_properties, mesh_properties, compare
from bsa.engine import ProjectError


class CADIFCTests(unittest.TestCase):
    def cube(self):
        m = manifold3d.Manifold.cube((1, 1, 1)).to_mesh64()
        return np.array(m.vert_properties), np.array(m.tri_verts)

    def test_known_closed_cube_and_readonly_arrays(self):
        vertices, faces = self.cube(); vertices.flags.writeable = False
        result = mesh_properties(vertices, faces)
        self.assertAlmostEqual(result['volume'], 1)
        self.assertTrue(np.allclose(result['centroid'], [.5, .5, .5]))
        self.assertTrue(np.array_equal(result['bounds'], [[0, 0, 0], [1, 1, 1]]))

    def test_unrestored_translation_and_wrong_scale_reject_comparison(self):
        v, f = self.cube(); ref = mesh_properties(v, f)
        moved = compare(mesh_properties(v+10, f), ref, 1e-8, 1e-8)
        self.assertTrue(moved['volume']); self.assertFalse(moved['bounds']); self.assertFalse(moved['centroid'])
        wrong = compare(mesh_properties(v*1000, f), ref, 1e-8, 1e-8)
        self.assertFalse(any(wrong.values()))

    def test_open_mesh_rejected(self):
        v, f = self.cube()
        with self.assertRaises(ProjectError): mesh_properties(v, f[:-1])

    def test_mass_properties_missing_and_ambiguous_rejected(self):
        text = 'Volume: 1.0\nBounding box: X: 0 -- 1\nY: 0 -- 1\nZ: 0 -- 1\nCentroid: X: 0.5\nY: 0.5\nZ: 0.5\n'
        result = mass_properties(text)
        self.assertEqual(result['volume'], 1)
        for bad in ('', text+text, text.replace('Volume: 1.0', 'Volume: -1.0')):
            with self.assertRaises(ProjectError): mass_properties(bad)
