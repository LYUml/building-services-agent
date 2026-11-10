import math
import unittest
from bsa.duct_equivalent import calculate


class EquivalentDuctTests(unittest.TestCase):
    def run_case(self, **overrides):
        args=dict(flow_m3_s=1, width_m=.8, height_m=.4,
                  density_kg_m3=1.2, viscosity_Pa_s=1.81e-5, roughness_m=.00009)
        args.update(overrides)
        return calculate(**args)

    def test_published_diameter_table(self):
        # ASHRAE 2021 ch21 Table3, published integer-mm rounding.
        for w,h,de in [(.8,.4,609),(1,.5,762),(1.2,.6,914)]:
            r=self.run_case(width_m=w,height_m=h)
            self.assertAlmostEqual(r['equivalent_diameter_m']*1000,de,delta=.6)

    def test_velocity_and_colebrook_residual(self):
        r=self.run_case()
        self.assertAlmostEqual(r['actual_velocity_m_s'],3.125)
        self.assertNotAlmostEqual(r['actual_velocity_m_s'],r['equivalent_round_velocity_m_s'])
        f=r['darcy_factor']; de=r['equivalent_diameter_m']; re=r['reynolds']
        residual=1/math.sqrt(f)+2*math.log10(.00009/de/3.7+2.51/(re*math.sqrt(f)))
        self.assertAlmostEqual(residual,0,places=9)

    def test_invalid_and_unsupported_inputs(self):
        for kw in [dict(flow_m3_s=.000001),dict(width_m=0),dict(roughness_m=-1),
                   dict(viscosity_Pa_s=float('nan')),dict(flow_m3_s=True)]:
            with self.assertRaises(ValueError): self.run_case(**kw)
