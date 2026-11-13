import unittest
from bsa.contraction_candidate import interpolate,screen


class ContractionCandidateTests(unittest.TestCase):
    def data(self):return dict(_theta=[0.,10.],_L_on_D=[0.,1.],_A_on_A1=[0.,1.],_k_A=[1.,0.],_zeta=[[0.,10.],[100.,110.]])

    def test_axis_orientation_bilinear_area_factor_and_bounds(self):
        self.assertEqual(interpolate(self.data(),5.,.5,.5),27.5)
        self.assertEqual(interpolate(self.data(),2.5,.75,.5),38.75)
        for query in [(11.,.5,.5),(5.,1.1,.5),(5.,.5,-.1),(float('nan'),.5,.5)]:
            with self.assertRaises(ValueError):interpolate(self.data(),*query)

    def test_unequal_angles_never_replaced_by_maximum(self):
        request=dict(product_guid='fictional',recorded_table_result=None,transition_geometry=dict(flow_change='contraction',quantities=dict(taper_width_angle_deg=2.,taper_height_angle_deg=8.)))
        r=screen(request,self.data());self.assertEqual(r['status'],'no_single_equal_wall_angle');self.assertIsNone(r['candidate_coefficient'])
