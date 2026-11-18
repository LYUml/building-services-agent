import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import ezdxf

from bsa.source_refs import file_hash
from bsa.dwg_readback import run


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'docs/evidence/drawing-intake'
RUNTIME = ('BSA_ACADSHARP_DOTNET', 'BSA_ACADSHARP_WORKER')


@unittest.skipUnless(all(os.environ.get(key) for key in RUNTIME) and importlib.util.find_spec('mcp'),
                     'requires the configured ACadSharp worker and MCP SDK')
class DwgReadbackTests(unittest.TestCase):
    def test_cli_and_mcp_match_native_export_and_preserve_source(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        source = FIXTURE / 'synthetic-base.dwg'
        original = file_hash(source)
        runs = ROOT / 'runs'
        runs.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=runs) as temporary:
            output = Path(temporary)
            cli_report = output / 'cli.json'
            mcp_report = output / 'mcp.json'
            env = {**os.environ, 'BSA_PROJECT_ROOT': str(ROOT)}
            reference = FIXTURE / 'source-export.dxf'
            command = [sys.executable, '-m', 'bsa.cli', 'dwg-readback', str(source), '--out', str(cli_report),
                       '--reference-dxf', str(reference)]
            summary = json.loads(subprocess.check_output(command, cwd=ROOT, env=env))

            async def read_mcp():
                params = StdioServerParameters(command=sys.executable, args=['-m', 'bsa.mcp_server'],
                                               cwd=str(ROOT), env=env)
                async with stdio_client(params) as (receive, send):
                    async with ClientSession(receive, send) as session:
                        await session.initialize()
                        args = dict(source=source.relative_to(ROOT).as_posix(), out=mcp_report.relative_to(ROOT).as_posix())
                        args['reference_dxf'] = reference.relative_to(ROOT).as_posix()
                        result = await session.call_tool('bsa_read_dwg_inventory', args)
                        self.assertFalse(result.isError, result.content)
                        self.assertEqual(result.structuredContent['report_sha256'], summary['report_sha256'])
                        repeated = await session.call_tool('bsa_read_dwg_inventory', args)
                        self.assertTrue(repeated.isError)

            asyncio.run(read_mcp())
            self.assertEqual(cli_report.read_bytes(), mcp_report.read_bytes())
            report = json.loads(cli_report.read_bytes())
            self.assertTrue(summary['correspondence_pass'])
            self.assertEqual(summary['insunits'], 4)
            self.assertEqual(report['comparison']['geometry_compared_count'], 4)
            self.assertEqual(report['source_sha256'], original)
            expected = {e.dxf.handle: e for e in ezdxf.readfile(FIXTURE / 'source-export.dxf').modelspace()}
            actual = {row['handle']: row for row in report['entities']}
            self.assertEqual({h: (r['type'], r['layer']) for h, r in actual.items()},
                             {h: (e.dxftype(), e.dxf.layer) for h, e in expected.items()})
            for handle, entity in expected.items():
                geometry = actual[handle]['geometry']
                if entity.dxftype() == 'LINE':
                    self.assertEqual(geometry, dict(start=list(entity.dxf.start), end=list(entity.dxf.end)))
                elif entity.dxftype() == 'TEXT':
                    self.assertEqual(geometry, dict(text=entity.dxf.text, insert=list(entity.dxf.insert),
                                                    height=entity.dxf.height))
                elif entity.dxftype() == 'LWPOLYLINE':
                    self.assertEqual(geometry['vertices'], [list(v) for v in entity.get_points('xyseb')])
                    self.assertEqual(geometry['closed'], entity.closed)
                elif entity.dxftype() == 'INSERT':
                    self.assertEqual(geometry['block_name'], entity.dxf.name)
                    self.assertEqual(geometry['insert'], list(entity.dxf.insert))
                else:
                    self.assertIsNone(geometry)
            self.assertFalse(report['native_autocad_executed'])
            self.assertEqual(file_hash(source), original)

            changed = ezdxf.readfile(reference)
            line = changed.modelspace().query('LINE')[0]
            line.dxf.end += (1, 0, 0)
            insert = changed.modelspace().query('INSERT')[0]
            insert.dxf.rotation += 15
            changed.units = 6
            changed_dxf, difference_report = output / 'changed.dxf', output / 'differences.json'
            changed.saveas(changed_dxf)
            mismatch = subprocess.run(command[:-4] + ['--out', str(difference_report),
                                                       '--reference-dxf', str(changed_dxf)],
                                      cwd=ROOT, env=env, capture_output=True, check=False)
            self.assertEqual(mismatch.returncode, 2, mismatch.stderr)
            comparison = json.loads(difference_report.read_bytes())['comparison']
            self.assertEqual(comparison['differences'], [dict(reason='drawing_units_differ', dwg_insunits=4, dxf_insunits=6)] + [
                dict(handle=handle, reason='geometry_differs') for handle in sorted((line.dxf.handle, insert.dxf.handle))
            ])
            stale_report = output / 'stale.json'
            with self.assertRaisesRegex(ValueError, 'differs from the verified revision artifact hashes'):
                run(source, stale_report, changed_dxf, expected_hashes=(original, file_hash(reference)))
            self.assertFalse(stale_report.exists())
