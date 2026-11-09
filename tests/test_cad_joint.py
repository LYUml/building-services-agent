import unittest
import numpy as np
from bsa.cad_joint import insertion
from bsa.engine import ProjectError


class NativeJointTests(unittest.TestCase):
    def test_rotated_nonzero_base_compensation(self):
        point, rotation = insertion([2,3,4], [10,20,30], 90)
        np.testing.assert_allclose(point, [7,22,34])
        # CAD import subtracts its base point before insertion.
        local = np.array([5,7,9])
        np.testing.assert_allclose(rotation@(local-[2,3,4])+point, [3,25,39])

    def test_invalid_transform_rejected(self):
        for base, translation, angle in [([0,0], [0,0,0], 0),
                                         ([0,0,0], [0,float('nan'),0], 0),
                                         ([0,0,0], [0,0,0], float('inf'))]:
            with self.assertRaises(ProjectError):
                insertion(base, translation, angle)

    def test_three_dimensional_rotation_and_invalid_matrices(self):
        rotation=np.array([[0.,1,0],[0,0,-1],[-1,0,0]])
        point,observed=insertion([2,3,4],[10,20,30],rotation)
        np.testing.assert_allclose(point,[13,16,28])
        np.testing.assert_array_equal(observed,rotation)
        for invalid in (np.diag([-1.,1,1]),np.diag([2.,1,1]),np.full((3,3),np.nan)):
            with self.assertRaises(ProjectError):insertion([0,0,0],[0,0,0],invalid)
