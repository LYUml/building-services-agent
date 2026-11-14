import unittest
from shapely.geometry import Polygon,box,Point
from bsa.manufacturer_adpi import curve_value,screen,lengths,grid,evaluate


class ManufacturerComparisonTests(unittest.TestCase):
    def setUp(self):
        self.curves=dict(fragments=[dict(load_Btuh_ft2=load,points=[[.5,70],[1.,90],[1.5,70]]) for load in (20,40,60)],stroke_width_ratio=.01,stroke_width_ADPI_points=.1)

    def test_native_curve_interpolation_and_no_extrapolation(self):
        self.assertEqual(curve_value(self.curves,40,.75),80)
        self.assertIsNone(curve_value(self.curves,40,.4))
        self.assertIsNone(curve_value(self.curves,50,1))
        self.assertEqual(screen(self.curves,40,1)['status'],'paired_curve_threshold_met')
        self.assertEqual(screen(self.curves,40,.75)['status'],'below_paired_curve_threshold')

    def test_fragment_gap_is_not_filled(self):
        self.curves['fragments']=[dict(load_Btuh_ft2=40,points=[[.5,80],[.8,90]]),dict(load_Btuh_ft2=40,points=[[.9,90],[1.2,80]])]
        self.assertIsNone(curve_value(self.curves,40,.85))
        self.assertEqual(screen(self.curves,40,.805)['status'],'outside_published_curve_or_fragment_domain')

    def test_aligned_midplane_and_actual_hole_ray(self):
        boundary=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(4,4),(6,4),(6,6),(4,6)]])
        ts=[dict(id='a',center_m=[2,5]),dict(id='b',center_m=[2,9])]
        result=lengths(boundary,ts)
        self.assertEqual(result['a'],dict(east=2,west=2,north=2,south=5))
        ts[1]['center_m']=[2.1,9]
        self.assertEqual(lengths(boundary,ts)['a']['north'],5)

    def test_two_zone_grid_ignores_zero_area_boundary_tail(self):
        boundary=Polygon([(0,0),(10,0),(10,10),(8,10),(8,5),(0,5)])
        points=grid(boundary,5,[[4,2],[2,2]])
        self.assertEqual(len(points),12)
        self.assertTrue(all(boundary.contains(Point(t['center_m'])) for t in points))
        self.assertTrue(all(t['center_m'][0]>=8 for t in points if t['id'].startswith('bay')))

    def test_infeasible_table_not_converted_to_conditional_pass(self):
        row=lambda q:dict(flow_L_s=q,T025_m=1,static_pressure_Pa=1,total_pressure_Pa=2,NC=None,NC_qualifier='less than 10')
        allocation=dict(terminals=[dict(id='a',maximum_flow_L_s=100,minimum_flow_L_s=40)])
        directions=dict(a=dict(east=1,west=1,north=1,south=1))
        result=evaluate(allocation,directions,{'8':[row(50),row(150)]},self.curves)[0]
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(result['failure_reason_counts'],dict(outside_original_performance_table=1))


if __name__=='__main__':unittest.main()
