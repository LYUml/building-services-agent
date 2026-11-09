import unittest
import numpy as np
from bsa.alignment_native import relative_basis
from bsa.engine import ProjectError


class AlignmentNativeTests(unittest.TestCase):
    def test_common_project_rotation_cancels_and_units_convert(self):
        fixed=np.array([[1.,0,0,8],[0,0,-1,9],[0,1,0,10],[0,0,0,1]])
        local=np.array([[0.,1,0,.07],[-1,0,0,.02],[0,0,1,.03],[0,0,0,1]])
        shift,rotation=relative_basis(fixed,fixed@local,.001)
        np.testing.assert_allclose(shift,[70,20,30])
        np.testing.assert_allclose(rotation,local[:3,:3])

    def test_relative_tilt_preserved_and_invalid_scale_rejected(self):
        tilted=np.array([[1.,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
        _,rotation=relative_basis(np.eye(4),tilted,1)
        np.testing.assert_allclose(rotation,tilted[:3,:3])
        with self.assertRaises(ProjectError):relative_basis(np.eye(4),np.eye(4),0)
