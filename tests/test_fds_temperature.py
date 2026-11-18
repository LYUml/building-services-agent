import tempfile
import unittest
from pathlib import Path

from bsa.fds_temperature import inspect_steps, point_temperature_errors


class FdsTemperatureTests(unittest.TestCase):
    def test_point_temperature_preserves_deviation_and_rejects_wrong_units(self):
        rows = ''.join(f'{time},22.5,22.5\n' for time in (0, 0.2, 0.45, 0.65, 0.8, 1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'points.csv'
            path.write_text(f's,C,C\nTime,center,off_center\n{rows}', encoding='ascii')
            self.assertEqual(point_temperature_errors(path), dict(center=0, off_center=0))
            path.write_text(f's,C,C\nTime,center,off_center\n{rows.replace("1,22.5,22.5", "1,22.5,23.5")}',
                            encoding='ascii')
            self.assertEqual(point_temperature_errors(path), dict(center=0, off_center=1))
            path.write_text(f's,K,C\nTime,center,off_center\n{rows}', encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'table layout'):
                point_temperature_errors(path)

    def test_matching_progression_and_forged_final_row(self):
        header = ',,s,s,s\nTime Step,Wall Time,Step Size,Simulation Time,CPU Time\n'
        rows = '1,recorded,0.01,0.01,0\n100,recorded,0.01,1,0.5\n20000,recorded,0.01,200,10\n'
        console = (' Time Step: 1, Simulation Time: 0.01 s\n'
                   ' Time Step: 100, Simulation Time: 1 s\n'
                   ' Time Step: 20000, Simulation Time: 200 s\n')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'steps.csv'
            path.write_text(header + rows, encoding='ascii')
            self.assertEqual(inspect_steps(path, console),
                             dict(report_samples=3, final_step=20000, final_simulation_s=200))
            for corrupted in (
                rows.replace('100,recorded,0.01,1,0.5\n', ''),
                rows.replace('20000,', '20001,'),
                rows.replace('0.01,1,0.5', '0.01,0.001,0.5'),
                rows.replace('0.01,1,0.5', 'nan,1,0.5'),
            ):
                with self.subTest(rows=corrupted):
                    path.write_text(header + corrupted, encoding='ascii')
                    with self.assertRaises(ValueError):
                        inspect_steps(path, console)
