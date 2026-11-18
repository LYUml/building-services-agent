from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from bsa.openfoam_transient import read_samples, difference, window_statistics


class PhysicalTimeHistoryTests(unittest.TestCase):
    def test_project_pressure_review_preserves_time_and_rejects_unmatched_history(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root/'basis.txt').write_text('Synthetic observer and pressure basis', encoding='utf-8')
            (root/'in.dat').write_text('# Time average(Pt)\n0 -2\n0.25 0\n0.5 2\n', encoding='utf-8')
            (root/'out.dat').write_text('# Time average(Ptf)\n0 -3\n0.25 -1\n0.5 1\n', encoding='utf-8')
            manifest = dict(schema='bsa.openfoam-pressure-history.v1', units='Pa', delta_t_s='0.25',
                            inlet=dict(file='in.dat', column='average(Pt)'), outlet=dict(file='out.dat', column='average(Ptf)'),
                            windows={'comparison': ['0', '0.5']}, basis_files={'observer': 'basis.txt'})
            (root/'pressure.json').write_text(json.dumps(manifest), encoding='utf-8')
            command = [sys.executable, '-m', 'bsa.cli', 'openfoam-pressure-review', '--manifest',
                       'pressure.json', '--output']
            env = {**os.environ, 'BSA_PROJECT_ROOT': str(root)}
            cli = subprocess.run(command+['checked.json'], env=env, capture_output=True, text=True)
            self.assertEqual(cli.returncode, 0, cli.stderr)
            review = json.loads(cli.stdout)
            self.assertEqual(review['windows']['comparison']['time_weighted_mean'], 1)
            self.assertFalse(review['engineering_accepted'])
            self.assertEqual(json.loads((root/'checked.json').read_bytes()), review)
            (root/'out.dat').write_text('# Time average(Ptf)\n0.25 -3\n0.5 -1\n0.75 1\n', encoding='utf-8')
            cli = subprocess.run(command+['rejected.json'], env=env, capture_output=True, text=True)
            self.assertEqual(cli.returncode, 2)
            self.assertIn('Exactly matching physical times required', cli.stderr)
            self.assertFalse((root/'rejected.json').exists())

    def read(self, rows):
        return read_samples('# Time average(Pt)\n'+rows,
                            'average(Pt)', delta_t_s='0.25')

    def test_physical_time_signed_difference_and_quadrature(self):
        a = self.read('0.00 -2\n0.25 0\n0.50 2\n')
        b = self.read('0.00 -3\n0.25 -1\n0.50 1\n')
        result = window_statistics(difference(a, b), '0', '0.5')
        self.assertEqual(result['time_weighted_mean'], 1)
        self.assertEqual(result['time_weighted_rms'], 0)
        self.assertFalse(result['stationarity_accepted'])
        self.assertEqual(a[1][0], Decimal('0.25'))

    def test_restart_overlap_missing_row_and_partial_write_rejected(self):
        for text in ('0 1\n0 2\n', '0 1\n0.5 2\n', '0 1\n0.25 2'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read(text)

    def test_no_time_alignment_or_endpoint_guessing(self):
        a = self.read('0 1\n0.25 2\n0.5 3\n')
        b = self.read('0.25 1\n0.5 2\n0.75 3\n')
        with self.assertRaises(ValueError):
            difference(a, b)
        with self.assertRaises(ValueError):
            window_statistics(a, '0.1', '0.5')
        with self.assertRaises(ValueError):
            window_statistics(a, 0.0, '0.5')

    def test_nonfinite_and_unrepresentable_quadrature_rejected(self):
        with self.assertRaises(ValueError):
            self.read('0 nan\n')
        with self.assertRaises(ValueError):
            window_statistics([(Decimal(0), 1e308), (Decimal(1), -1e308)], '0', '1')


if __name__ == '__main__':
    unittest.main()
