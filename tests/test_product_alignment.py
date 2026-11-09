import unittest
import numpy as np
from bsa.product_alignment import aligned_placement
from bsa.engine import ProjectError


class ProductAlignmentTests(unittest.TestCase):
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
