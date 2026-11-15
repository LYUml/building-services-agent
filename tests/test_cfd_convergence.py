import unittest
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from bsa.cfd_convergence import assess


def history():
    return [dict(Inner_Iter=i, **{'Avg_Massflow(in)': 2., 'Avg_Massflow(out)': -2.,
                                'Avg_TotalPress(in)': 100.+i, 'Avg_TotalPress(out)': 20.+i})
            for i in range(3)]


class ConvergenceTests(unittest.TestCase):
    def check(self, rows, **kw):
        return assess(rows, {'in': 2., 'out': -2.}, 'in', window=3, **kw)

    def test_common_gauge_drift_cancels_without_engineering_acceptance(self):
        r = self.check(history())
        self.assertTrue(r['numerical_window_pass'])
        self.assertEqual(r['pressures']['out']['mean_Pa'], 80.)
        self.assertFalse(r['engineering_accepted'])

    def test_last_good_iteration_cannot_hide_failed_window(self):
        rows = history()
        rows[0]['Avg_Massflow(out)'] = -1.
        self.assertFalse(self.check(rows)['numerical_window_pass'])

    def test_conservation_cannot_hide_reversed_flows(self):
        rows = history()
        for row in rows:
            row['Avg_Massflow(in)'], row['Avg_Massflow(out)'] = -2., 2.
        r = self.check(rows)
        self.assertTrue(r['mass_pass'])
        self.assertFalse(r['flow_pass'])

    def test_negative_total_drop_not_clamped(self):
        rows = history()
        for row in rows:
            row['Avg_TotalPress(out)'] = 200.
        r = self.check(rows)
        self.assertLess(r['pressures']['out']['mean_Pa'], 0.)
        self.assertFalse(r['pressure_stability_pass'])

    def test_invalid_window_values_and_targets_rejected(self):
        with self.assertRaises(ValueError):
            self.check(history()[:2])
        rows = history()
        rows[1]['Inner_Iter'] = 4
        with self.assertRaises(ValueError):
            self.check(rows)
        for value in (float('nan'), True):
            rows = history()
            rows[0]['Avg_Massflow(in)'] = value
            with self.assertRaises(ValueError):
                self.check(rows)
        with self.assertRaises(ValueError):
            assess(history(), {'in': 2., 'out': -1.}, 'in', window=3)

    def test_cli_host_boundary_and_evidence_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (root/'history.csv').open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(history()[0]))
                writer.writeheader()
                writer.writerows(history())
            (root/'targets.json').write_text(json.dumps(dict(inlet='in', signed_mass_flow_targets_kg_s={'in': 2., 'out': -2.})))
            command = [sys.executable, '-m', 'bsa.cfd_convergence', '--history', 'history.csv',
                       '--targets', 'targets.json', '--output', 'review.json', '--window', '3']
            env = dict(os.environ, BSA_PROJECT_ROOT=str(root))
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            review = (root/'review.json').read_bytes()
            self.assertTrue(json.loads(review)['numerical_window_pass'])
            self.assertFalse(json.loads(review)['engineering_accepted'])
            self.assertNotEqual(subprocess.run(command, env=env, capture_output=True).returncode, 0)
            self.assertEqual((root/'review.json').read_bytes(), review)
            command[command.index('--output')+1] = '../outside-review.json'
            self.assertNotEqual(subprocess.run(command, env=env, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
