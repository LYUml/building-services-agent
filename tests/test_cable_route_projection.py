import math
import unittest
import numpy as np
from bsa.cable_route_drawing import project_geometry
from bsa.engine import ProjectError
from bsa.quarter_cable import points


class CableRouteProjectionTests(unittest.TestCase):
    def geometry(self, angle=0):
        c, s = math.cos(angle), math.sin(angle)
        frame = np.eye(4)
        frame[:3,:3] = [[c,0,s],[0,1,0],[-s,0,c]]
        frame[:3,3] = [4,-3,2]
        p = points(frame, .3)
        return np.vstack((p, p[-1]-2*frame[:3,0])), frame[:3,3]

    def test_all_quadrants_preserve_true_quarter(self):
        for theta in (0, .61, 2.4, 3.9, 5.9):
            p, c = self.geometry(theta)
            for axes in (['X','Z'], ['Z','X']):
                r = project_geometry(p, c, .3, axes)
                self.assertAlmostEqual((r['end_angle_deg']-r['start_angle_deg'])%360, 90)
                self.assertAlmostEqual(math.dist(*r['points_m'][2:]), 2)

    def test_end_on_projection_rejected(self):
        p,c = self.geometry()
        with self.assertRaisesRegex(ProjectError, 'projection plane'):
            project_geometry(p,c,.3,['X','Y'])

    def test_false_midpoint_rejected(self):
        p,c = self.geometry()
        p[1] = p[0]
        with self.assertRaisesRegex(ProjectError, 'quarter-circle'):
            project_geometry(p,c,.3,['X','Z'])

    def test_nonplanar_straight_rejected(self):
        p,c = self.geometry()
        p[-1,1]+=.01
        with self.assertRaisesRegex(ProjectError, 'projection plane'):
            project_geometry(p,c,.3,['X','Z'])
