import unittest
from bsa.cfd_flux_window import assess_flux_window


class FluxWindowTests(unittest.TestCase):
    def setUp(self):
        self.targets = {'in': -3., 'a': 1., 'b': 2.}
        self.rows = [{'step': i, 'fluxes': dict(self.targets)} for i in range(200)]

    def test_conservative_unequal_outlets(self):
        result = assess_flux_window(self.rows, self.targets)
        self.assertTrue(result['signed_flux_window_passed'])
        self.assertFalse(result['pressure_accepted'])

    def test_wrong_split_despite_exact_global_balance(self):
        self.rows[-1]['fluxes'].update(a=2., b=1.)
        self.assertFalse(assess_flux_window(self.rows, self.targets)['signed_flux_window_passed'])

    def test_reversed_flux_cannot_pass_using_magnitudes(self):
        self.rows[-1]['fluxes'] = {k: -v for k, v in self.targets.items()}
        self.assertFalse(assess_flux_window(self.rows, self.targets)['signed_flux_window_passed'])

    def test_missing_nonfinite_or_nonconsecutive_data_rejected(self):
        for mutation in ('missing', 'nan', 'duplicate'):
            self.setUp()
            if mutation == 'missing': del self.rows[-1]['fluxes']['b']
            if mutation == 'nan': self.rows[-1]['fluxes']['b'] = float('nan')
            if mutation == 'duplicate': self.rows[-1]['step'] = 198
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                assess_flux_window(self.rows, self.targets)


if __name__ == '__main__':
    unittest.main()
