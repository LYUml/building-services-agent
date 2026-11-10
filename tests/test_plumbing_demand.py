from math import comb
import unittest
from bsa.plumbing_demand import identical
from bsa.plumbing_demand import discharge_units


class DemandTests(unittest.TestCase):
    def test_discharge_aggregation_and_scope(self):
        rows=[dict(id='A',count=2,DU_per_fixture=3,source='Synthetic fixture',classification='assumed'),dict(id='B',count=1,DU_per_fixture=4,source='Synthetic fixture',classification='assumed')]
        r=discharge_units(rows,frequency_factor=.7,basis='Synthetic connected inventory and use')
        self.assertEqual(r['total_DU'],10);self.assertAlmostEqual(r['wastewater_flow_L_s'],.7*10**.5);self.assertFalse(r['design_accepted'])
        with self.assertRaises(ValueError):discharge_units(rows+rows,frequency_factor=.7,basis='Synthetic')
        with self.assertRaises(ValueError):discharge_units(rows,frequency_factor=None,basis='Synthetic')
        rows[0]['count']=True
        with self.assertRaises(ValueError):discharge_units(rows,frequency_factor=.7,basis='Synthetic')

    def call(self,**changes):
        return identical(**(dict(count=100,operating_probability=.01,fixture_flow_L_s=.1,exceedance_probability=.01,basis='Synthetic/lecture method verification; not project demand')|changes))
    def test_independent_tail_and_minimality(self):
        r=self.call();self.assertEqual(r['simultaneous_appliances'],4);self.assertAlmostEqual(r['design_flow_L_s'],.4)
        exact=sum(comb(100,k)*.01**k*.99**(100-k) for k in range(5,101))
        self.assertAlmostEqual(r['actual_exceedance_probability'],exact,places=13)
        self.assertGreater(r['previous_provision_exceedance_probability'],.01);self.assertFalse(r['design_accepted'])
    def test_zero_provision_and_full_provision(self):
        self.assertEqual(self.call(count=1,operating_probability=.001)['simultaneous_appliances'],0)
        self.assertEqual(self.call(count=1,operating_probability=.9)['simultaneous_appliances'],1)
    def test_stricter_service_is_monotone(self):
        counts=[self.call(exceedance_probability=p)['simultaneous_appliances'] for p in [.1,.01,.001]]
        self.assertEqual(counts,sorted(counts))
    def test_invalid_and_unknown_inputs(self):
        for changes in [dict(count=True),dict(count=0),dict(operating_probability=None),dict(exceedance_probability=0),dict(fixture_flow_L_s=float('nan')),dict(basis='')]:
            with self.assertRaises(ValueError):self.call(**changes)
