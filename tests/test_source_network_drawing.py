import unittest
import numpy as np
from bsa.source_network_drawing import project


class NativeProjectionTests(unittest.TestCase):
    def test_numerical_seam_cleanup_keeps_real_gaps_and_rejects_collapsed_geometry(self):
        v=[[0,0,0],[1,0,0],[0,1,0],[1,5e-10,0],[1,1,0],[5e-10,1,0]]
        self.assertEqual(len(project(v,[[0,1,2],[3,4,5]])),1)
        with self.assertRaises(ValueError):
            project([[0,0,0],[1,0,0],[0,1,0],[3,0,0],[3+1e-10,0,0],[3,1e-10,0]],[[0,1,2],[3,4,5]])

    def test_triangle_union_removes_internal_diagonals_without_bounding_box(self):
        v=[[0,0,0],[2,0,0],[2,1,0],[0,1,0],[1,1,1],[1,2,1],[0,2,1]]
        result=project(v,[[0,1,2],[0,2,3],[3,4,5],[3,5,6]])
        self.assertEqual(len(result),1);self.assertAlmostEqual(result[0].area,3.)
        self.assertEqual(result[0].bounds,(0.,0.,2.,2.))

    def test_disjoint_components_preserved_and_invalid_mesh_rejects(self):
        result=project([[0,0,0],[1,0,0],[0,1,0],[3,0,0],[4,0,0],[3,1,0]],[[0,1,2],[3,4,5]])
        self.assertEqual(len(result),2);self.assertAlmostEqual(sum(p.area for p in result),1.)
        for v,f in [([[0,0,0],[1,0,0],[0,1,float('nan')]],[[0,1,2]]),
                    ([[0,0,0],[1,0,0],[0,1,0]],[[0,1,3]]),
                    ([[0,0,0],[1,0,0],[0,1,0]],np.array([[0.,1.,2.]]))]:
            with self.assertRaises(ValueError):project(v,f)
