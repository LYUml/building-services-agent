import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('cable_probe', Path(__file__).resolve().parents[1]/'scripts/probe_cable_mesh.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class CableTopologyTests(unittest.TestCase):
    def test_closed_edges_do_not_hide_reversed_face(self):
        vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]])
        original = probe.topology(vertices, faces)
        self.assertEqual(original['inconsistent_direction_edges'], 0)
        self.assertEqual(original['non_two_face_edges'], 0)
        faces[0] = faces[0, ::-1]
        reversed_face = probe.topology(vertices, faces)
        self.assertEqual(reversed_face['non_two_face_edges'], 0)
        self.assertEqual(reversed_face['euler'], 2)
        self.assertEqual(reversed_face['inconsistent_direction_edges'], 3)

    def test_missing_face_and_duplicate_are_visible(self):
        vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3]])
        self.assertEqual(probe.topology(vertices, faces)['non_two_face_edges'], 3)
        self.assertEqual(probe.topology(vertices, np.vstack([faces, faces[0]]))['duplicate_triangles'], 1)
