from math import comb
import unittest
from bsa.plumbing_demand import identical


class DemandTests(unittest.TestCase):
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
