import unittest
import numpy as np
from bsa.product_alignment import aligned_placement, overlap_locations
from bsa.engine import ProjectError


class ProductAlignmentTests(unittest.TestCase):
    def test_overlap_locations_in_rotated_translated_port_frame(self):
        import manifold3d as m
        frame=np.array([[0.,-1,0,10],[1,0,0,20],[0,0,1,30],[0,0,0,1]])
        # World box [9,20,30]..[10,22,33] maps to local [0,0,0]..[2,1,3].
        common=m.Manifold.cube((1,2,3)).translate((9,20,30))
        rows=overlap_locations(common,frame)
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]['volume_m3'],6)
        self.assertTrue(np.allclose(rows[0]['port_frame_bounds_m'],[[0,0,0],[2,1,3]]))
        self.assertAlmostEqual(rows[0]['maximum_radius_from_port_axis_m'],np.sqrt(5))
        self.assertEqual(overlap_locations(m.Manifold(),frame),[])

    def test_offset_node_roll_and_opposing_axis(self):
        target=np.eye(4);target[:3,3]=[4,5,6]
        local=np.eye(4);local[:3,3]=[0,0,-.2]
        result=aligned_placement(target,local,90)
        port=result@local
        self.assertTrue(np.allclose(port[:3,3],[4,5,6]))
        self.assertTrue(np.allclose(port[:3,2],[0,0,-1]))
        self.assertTrue(np.allclose(port[:3,0],[0,1,0]))
        self.assertAlmostEqual(np.linalg.det(result[:3,:3]),1)

    def test_rigid_frame_validation(self):
        for bad in (np.diag([2.,1,1,1]),np.diag([-1.,1,1,1]),np.full((4,4),np.nan)):
            with self.assertRaises(ProjectError):aligned_placement(np.eye(4),bad,0)
        with self.assertRaises(ProjectError):aligned_placement(np.eye(4),np.eye(4),float('nan'))
