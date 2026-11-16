import unittest
from bsa.openfoam_history import read_samples, to_convergence_rows


class NativeHistoryTests(unittest.TestCase):
    def test_signed_density_conversion_preserves_pressure(self):
        f = {'in': [(10, -2.), (11, -2.)], 'out': [(10, 2.), (11, 2.)]}
        p = {'in': [(10, -7.), (11, -7.)], 'out': [(10, -9.), (11, -9.)]}
        r = to_convergence_rows(f, p, 1.2)
        self.assertEqual(r[0]['Avg_Massflow(in)'], 2.4)
        self.assertEqual(r[0]['Avg_Massflow(out)'], -2.4)
        self.assertEqual(r[0]['Avg_TotalPress(in)'], -7.)

    def test_native_column_and_consecutive_rows(self):
        self.assertEqual(read_samples('# Time sum(phi)\n10 -2\n11 -2\n', 'sum(phi)'), [(10, -2.), (11, -2.)])
        for text in ['# Time average(Pt)\n10 2\n', '# Time sum(phi)\n10 2\n10 2\n',
                     '# Time sum(phi)\n10 2\n12 2\n', '# Time sum(phi)\n10 nan\n',
                     '# Time sum(phi)\n10.5 2\n', '# Time sum(phi)\n10\n',
                     '# Time sum(phi)\n10 2']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                read_samples(text, 'sum(phi)')

    def test_no_silent_alignment_or_nonfinite_density(self):
        for p, rho in [({'a': [(2, 3.)]}, 1.2), ({'b': [(1, 3.)]}, 1.2),
                       ({'a': [(1, 3.)]}, float('nan'))]:
            with self.subTest(p=p, rho=rho), self.assertRaises(ValueError):
                to_convergence_rows({'a': [(1, 2.)]}, p, rho)


if __name__ == '__main__':
    unittest.main()
