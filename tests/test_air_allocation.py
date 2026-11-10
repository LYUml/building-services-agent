import unittest
from shapely.geometry import box,mapping
from bsa.air_allocation import prepare
from bsa.air_load import UNITS


class AirAllocationTests(unittest.TestCase):
    def test_layout_change_updates_flows_and_preserves_totals(self):
        values=dict(area=100,cooling_allowance=200,sensible_fraction=.8,density=1.25,specific_heat=1000,temperature_difference=10)
        inputs={k:dict(value=v,unit=UNITS[k],source='Synthetic test',classification='assumed') for k,v in values.items()}
        for right,expected_fraction in [(5,.3),(7,.4)]:
            with self.subTest(right=right):
                r=prepare(mapping(box(0,0,10,4)),[dict(id='A',center_m=[1,2]),dict(id='B',center_m=[right,2])],inputs,.4)
                self.assertAlmostEqual(r['terminals'][0]['maximum_flow_L_s'],1280*expected_fraction)
                self.assertAlmostEqual(r['terminals'][0]['minimum_flow_L_s'],1280*expected_fraction*.4)
                self.assertAlmostEqual(r['checks']['allocated_flow_L_s'],1280)
                self.assertFalse(r['design_accepted'])
                self.assertEqual(r['load']['inputs'],inputs)

    def test_invalid_turndown_precedes_calculation(self):
        for value in (0,1.1,True,float('nan')):
            with self.subTest(value=value),self.assertRaises(ValueError):prepare({},[],{},value)
