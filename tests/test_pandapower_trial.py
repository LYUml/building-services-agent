"""Execute only in the pinned isolated runtime; no native CAD/BIM acceptance."""
import importlib.util
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('pandapower'),'requires isolated pandapower trial runtime')
class PandapowerTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trial=staticmethod(runpy.run_path(str(ROOT/'scripts/probe_pandapower.py'))['trial'])

    def test_balanced_analytic_unbalanced_and_overload(self):
        balanced=self.trial([5,5,5]);unbalanced=self.trial([10,5,2]);overload=self.trial([30,5,2])
        self.assertTrue(balanced['verification_pass'])
        self.assertLess(balanced['balanced_analytic_error_v'],1e-5)
        self.assertTrue(unbalanced['verification_pass'])
        self.assertGreater(max(unbalanced['phase_current_a'])-min(unbalanced['phase_current_a']),1)
        self.assertTrue(overload['verification_pass'])
        self.assertFalse(overload['synthetic_current_target_pass'])
        self.assertFalse(overload['design_accepted'])

    def test_wrong_current_voltage_angle_and_source_power_are_detected(self):
        import pandapower as pp
        original=pp.runpp_3ph
        for field,expected in [('current','currents'),('angle','line_equations'),('power','power_balance'),('reactive','reactive_power')]:
            def altered(net,**kwargs):
                original(net,**kwargs)
                if field=='current':net.res_line_3ph.loc[0,'i_a_to_ka']+=0.001
                if field=='angle':net.res_bus_3ph.loc[1,'va_a_degree']+=0.1
                if field=='power':net.res_ext_grid_3ph.loc[0,'p_a_mw']+=0.0001
                if field=='reactive':net.res_ext_grid_3ph.loc[0,'q_a_mvar']+=0.0001
            with self.subTest(field=field),patch.object(pp,'runpp_3ph',side_effect=altered):
                result=self.trial([10,5,2])
                self.assertFalse(result['verification_pass'])
                self.assertFalse(result['verification_checks'][expected])


if __name__=='__main__':unittest.main()
