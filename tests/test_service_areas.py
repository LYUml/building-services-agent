import unittest
from shapely.geometry import box, mapping, shape
from shapely import union_all
from bsa.service_areas import allocate


class ServiceAreaTests(unittest.TestCase):
    def test_asymmetric_split_preserves_given_area(self):
        r = allocate(mapping(box(0,0,10,4)), [dict(id='A',center_m=[1,2]),dict(id='B',center_m=[5,2])], 100)
        self.assertAlmostEqual(r['terminals'][0]['geometric_area_m2'],12)
        self.assertAlmostEqual(r['terminals'][0]['allocated_load_area_m2'],30)
        self.assertEqual(r['net_geometry_area_m2'],40)
        self.assertFalse(r['design_accepted'])

    def test_concavity_and_column_remain_excluded(self):
        boundary=box(0,0,10,10).difference(box(5,5,10,10)).difference(box(1,1,2,2))
        r=allocate(mapping(boundary),[dict(id='A',center_m=[3,3]),dict(id='B',center_m=[3,8]),dict(id='C',center_m=[8,3])],70)
        cells=[shape(t['geometry']) for t in r['terminals']]
        self.assertLess(union_all(cells).symmetric_difference(boundary).area,1e-9)
        self.assertAlmostEqual(sum(t['allocated_load_area_m2'] for t in r['terminals']),70)

    def test_invalid_centres_rejected(self):
        for point in ([1,1],[20,20],[float('nan'),1],[0,1]):
            with self.subTest(point=point),self.assertRaises(ValueError):
                allocate(mapping(box(0,0,10,10)),[dict(id='A',center_m=[1,1]),dict(id='B',center_m=point)],100)
