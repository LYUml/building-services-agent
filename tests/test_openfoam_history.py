import unittest
import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from bsa.openfoam_history import read_samples, to_convergence_rows, review_project


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


class ProjectReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        env = patch.dict('os.environ', {'BSA_PROJECT_ROOT': str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        (self.root/'basis.txt').write_text('Synthetic fixture, not engineering evidence')
        patches = {}
        for name, q, p in [('in', -2., -7.), ('out', 2., -9.)]:
            files = {'flux': f'{name}-q.dat', 'total_pressure': f'{name}-p.dat'}
            for key, column, value in [('flux', 'sum(phi)', q), ('total_pressure', 'average(Pt)', p)]:
                (self.root/files[key]).write_text(f'# Time {column}\n1 {value}\n2 {value}\n')
            patches[name] = files
        self.manifest = {
            'schema': 'bsa.openfoam-history.v1', 'units': {'phi': 'm3/s', 'Pt': 'Pa'},
            'time_basis': 'steady_deltaT_1', 'density_kg_m3': 1.2, 'inlet': 'in',
            'outward_volume_targets_m3_s': {'in': -2., 'out': 2.},
            'basis_files': {'fixture': 'basis.txt'}, 'patches': patches,
        }

    def write_manifest(self):
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))

    def test_small_window_is_explicit_and_existing_output_preserved(self):
        self.write_manifest()
        result = review_project('manifest.json', 'review.json', window=2)
        self.assertTrue(result['numerical_window_pass'])
        self.assertFalse(result['complete_200_step_window'])
        self.assertFalse(result['engineering_accepted'])
        before = (self.root/'review.json').read_bytes()
        with self.assertRaises(ValueError):
            review_project('manifest.json', 'review.json', window=2)
        self.assertEqual(before, (self.root/'review.json').read_bytes())

    def test_basis_escape_and_wrong_units_rejected(self):
        self.manifest['basis_files'] = {'escape': '../outside.txt'}
        self.write_manifest()
        with self.assertRaises(ValueError):
            review_project('manifest.json', 'review.json', window=2)
        self.manifest['basis_files'] = {'fixture': 'basis.txt'}
        self.manifest['units']['Pt'] = 'm2/s2'
        self.write_manifest()
        with self.assertRaises(ValueError):
            review_project('manifest.json', 'review.json', window=2)

    def test_cli_and_stdio_review_same_saved_segment(self):
        self.write_manifest()
        args = [sys.executable, '-m', 'bsa.cli', 'openfoam-history-review', '--manifest',
                'manifest.json', '--window', '2', '--output']
        cli = subprocess.run(args + ['cli.json'], capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        expected = json.loads(cli.stdout)
        denied = subprocess.run(args + ['../escaped.json'], capture_output=True, text=True)
        self.assertEqual(denied.returncode, 2, denied.stderr)
        self.assertIn('remain inside the host project', denied.stderr)
        if importlib.util.find_spec('mcp'):
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            async def compare():
                params = StdioServerParameters(command=sys.executable, args=['-m', 'bsa.mcp_server'],
                                               cwd=str(self.root), env=dict(os.environ))
                arguments = dict(manifest='manifest.json', output='mcp.json', window=2)
                async with stdio_client(params) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        result = await session.call_tool('bsa_review_openfoam_history', arguments)
                        self.assertFalse(result.isError, result.content)
                        self.assertEqual(result.structuredContent, expected)
                        escaped = await session.call_tool('bsa_review_openfoam_history',
                                                          {**arguments, 'output': '../escaped.json'})
                        self.assertTrue(escaped.isError)

            asyncio.run(compare())

    def test_wrong_observation_window_cannot_be_accepted(self):
        self.manifest['expected_window'] = [2, 3]
        self.write_manifest()
        with self.assertRaises(ValueError):
            review_project('manifest.json', 'review.json', window=2)
        self.assertFalse((self.root/'review.json').exists())

    def test_native_history_changed_during_assessment_is_rejected(self):
        from bsa import cfd_convergence
        self.write_manifest()
        assess = cfd_convergence.assess

        def assess_then_change(*args, **kwargs):
            result = assess(*args, **kwargs)
            pressure = self.root/'in-p.dat'
            pressure.write_text(pressure.read_text() + '3 -7\n')
            return result

        with patch('bsa.cfd_convergence.assess', side_effect=assess_then_change):
            with self.assertRaisesRegex(ValueError, 'input changed: in-p.dat'):
                review_project('manifest.json', 'review.json', window=2)
        self.assertFalse((self.root/'review.json').exists())


if __name__ == '__main__':
    unittest.main()
