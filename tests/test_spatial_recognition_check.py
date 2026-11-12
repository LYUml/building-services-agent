import copy
import unittest
from bsa.spatial_recognition_check import check


class SpatialRecognitionCheckTests(unittest.TestCase):
    def setUp(self):
        self.expected=[dict(id='source',boundary_vertices=[[0,0],[5,0],[5,2],[2,2],[2,4],[0,4]],height_m=3)]
        self.actual=[dict(self.expected[0],id='generated-id',is_open=False)]

    def check(self,actual=None,expected=None):
        return check(self.actual if actual is None else actual,self.expected if expected is None else expected,length_tolerance_m=1e-6,area_tolerance_m2=1e-8)

    def test_identity_independent_boundary_and_source_coverage(self):
        self.assertTrue(self.check()['source_geometry_matches'])
        self.assertFalse(self.check(actual=[])['source_geometry_matches'])
        self.assertFalse(self.check(actual=self.actual+[dict(self.actual[0],id='extra')])['source_geometry_matches'])
        self.assertFalse(self.check(actual=[dict(self.actual[0],is_open=True)])['source_geometry_matches'])

    def test_same_area_shift_and_height_change_reject(self):
        for kind in ('shift','height'):
            changed=copy.deepcopy(self.actual)
            if kind=='shift':changed[0]['boundary_vertices']=[[x+.0004,y] for x,y in changed[0]['boundary_vertices']]
            else:changed[0]['height_m']+=.001
            self.assertFalse(self.check(actual=changed)['source_geometry_matches'])

    def test_duplicate_and_invalid_geometry_reject(self):
        with self.assertRaisesRegex(ValueError,'identities'):self.check(actual=self.actual*2)
        with self.assertRaises(ValueError):check([],[],length_tolerance_m=True,area_tolerance_m2=1e-8)
        bad=copy.deepcopy(self.actual);bad[0]['boundary_vertices'][0][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'Finite'):self.check(actual=bad)

    def test_one_recognized_room_cannot_cover_duplicate_source_footprints(self):
        self.assertFalse(self.check(expected=self.expected+[dict(self.expected[0],id='another-source')])['source_geometry_matches'])
