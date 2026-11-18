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
from bsa.dwg_readback import compare_reference, dxf_geometry, run


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'docs/evidence/drawing-intake'
RUNTIME = ('BSA_ACADSHARP_DOTNET', 'BSA_ACADSHARP_WORKER')


def test_reports_types_without_geometry_coverage(tmp_path):
    document = ezdxf.new()
    solid = document.modelspace().add_solid([(0, 0), (1, 0), (0, 1)])
    reference = tmp_path / 'identity-only.dxf'
    document.saveas(reference)
    row = dict(handle=solid.dxf.handle, type='SOLID', layer='0', geometry=None)
    comparison = compare_reference([row], document.units, reference)
    assert comparison['correspondence_pass']
    assert comparison['geometry_compared_count'] == 0
    assert comparison['identity_only_counts_by_type'] == {'SOLID': 1}


def test_duplicate_reference_handle_cannot_hide_entity(tmp_path):
    document = ezdxf.new()
    modelspace = document.modelspace()
    displaced = modelspace.add_line((2, 2), (3, 3))
    expected = modelspace.add_line((0, 0), (1, 1))
    expected.dxf.handle = displaced.dxf.handle
    reference = tmp_path / 'duplicate.dxf'
    document.saveas(reference)
    row = dict(handle=expected.dxf.handle, type='LINE', layer='0',
               geometry=dict(start=[0, 0, 0], end=[1, 1, 0], normal=[0, 0, 1], thickness=0))
    comparison = compare_reference([row], document.units, reference)
    assert not comparison['correspondence_pass']
    assert comparison['geometry_compared_count'] == 0
    assert comparison['differences'] == [dict(handle=expected.dxf.handle, reason='duplicate_handle_in_dxf')]


def test_changed_equipment_attribute_is_a_block_difference(tmp_path):
    document = ezdxf.new()
    block = document.blocks.new('EQUIPMENT_TAG')
    block.add_attdef('EQUIPMENT_ID', (0, 0))
    insert = document.modelspace().add_blockref(block.name, (5, 5))
    insert.add_auto_attribs({'EQUIPMENT_ID': 'VAV-001'})
    row = dict(handle=insert.dxf.handle, type='INSERT', layer='0', geometry=dxf_geometry(insert))
    insert.get_attrib('EQUIPMENT_ID').dxf.text = 'VAV-002'
    reference = tmp_path / 'changed-attribute.dxf'
    document.saveas(reference)
    assert compare_reference([row], document.units, reference)['differences'] == [
        dict(handle=insert.dxf.handle, reason='geometry_differs', fields=['attributes'])]


def test_lists_multiline_attributes_whose_text_was_not_checked(tmp_path):
    from ezdxf.entities import MText

    document = ezdxf.new('R2018')
    block = document.blocks.new('EQUIPMENT_TAG')
    insert = document.modelspace().add_blockref(block.name, (5, 5))
    attribute = insert.add_attrib('NOTE', 'First line')
    attribute.embed_mtext(MText.new(dxfattribs={'text': 'First line\\PSecond line'}))
    reference = tmp_path / 'multiline.dxf'
    document.saveas(reference)
    row = dict(handle=insert.dxf.handle, type='INSERT', layer='0', geometry=dxf_geometry(insert))
    comparison = compare_reference([row], document.units, reference)
    assert comparison['correspondence_pass']
    assert comparison['unchecked_multiline_attribute_text'] == [
        dict(insert_handle=insert.dxf.handle, attribute_handle=attribute.dxf.handle, tag='NOTE')]


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
                        for field in ('geometry_compared_count', 'identity_only_counts_by_type',
                                      'source_sha256', 'reference_sha256', 'worker_sha256', 'reader_sha256'):
                            self.assertEqual(result.structuredContent[field], summary[field])
                        repeated = await session.call_tool('bsa_read_dwg_inventory', args)
                        self.assertTrue(repeated.isError)

            asyncio.run(read_mcp())
            self.assertEqual(cli_report.read_bytes(), mcp_report.read_bytes())
            report = json.loads(cli_report.read_bytes())
            self.assertEqual(report['schema'], 'bsa.acadsharp-modelspace/3')
            self.assertTrue(summary['correspondence_pass'])
            self.assertEqual(summary['insunits'], 4)
            self.assertEqual(report['comparison']['geometry_compared_count'], 5)
            self.assertEqual(summary['geometry_compared_count'], 5)
            self.assertEqual(summary['identity_only_counts_by_type'], {})
            self.assertEqual(report['source_sha256'], original)
            worker = Path(os.environ['BSA_ACADSHARP_WORKER'])
            reader = worker.with_name('ACadSharp.dll')
            self.assertEqual(report['reader_sha256'], file_hash(reader))
            self.assertEqual(summary['reader_sha256'], report['reader_sha256'])
            self.assertEqual(summary['worker_sha256'], file_hash(worker))
            self.assertEqual(summary['reference_sha256'], file_hash(reference))
            self.assertEqual(report['comparison']['reference_sha256'], summary['reference_sha256'])
            expected = {e.dxf.handle: e for e in ezdxf.readfile(FIXTURE / 'source-export.dxf').modelspace()}
            actual = {row['handle']: row for row in report['entities']}
            self.assertEqual({h: (r['type'], r['layer']) for h, r in actual.items()},
                             {h: (e.dxftype(), e.dxf.layer) for h, e in expected.items()})
            for handle, entity in expected.items():
                geometry = actual[handle]['geometry']
                if entity.dxftype() == 'LINE':
                    self.assertEqual(geometry, dict(start=list(entity.dxf.start), end=list(entity.dxf.end),
                                                    normal=list(entity.dxf.extrusion), thickness=entity.dxf.thickness))
                elif entity.dxftype() == 'POINT':
                    self.assertEqual(geometry, dict(location=list(entity.dxf.location)))
                elif entity.dxftype() == 'TEXT':
                    self.assertEqual(geometry['text'], entity.dxf.text)
                    self.assertEqual(geometry['insert'], list(entity.dxf.insert))
                    self.assertEqual(geometry['height'], entity.dxf.height)
                    self.assertEqual(geometry['style'], entity.dxf.style)
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
            line.dxf.extrusion = (0, 1, 0)
            line.dxf.thickness = 2
            point = changed.modelspace().query('POINT')[0]
            point.dxf.location += (0, 0, 1)
            insert = changed.modelspace().query('INSERT')[0]
            insert.dxf.rotation += 15
            label = changed.modelspace().query('TEXT')[0]
            label.dxf.rotation += 10
            changed.units = 6
            changed_dxf, difference_report = output / 'changed.dxf', output / 'differences.json'
            changed.saveas(changed_dxf)
            mismatch = subprocess.run(command[:-4] + ['--out', str(difference_report),
                                                       '--reference-dxf', str(changed_dxf)],
                                      cwd=ROOT, env=env, capture_output=True, check=False)
            self.assertEqual(mismatch.returncode, 2, mismatch.stderr)
            comparison = json.loads(difference_report.read_bytes())['comparison']
            affected_fields = {line.dxf.handle: ['end', 'normal', 'thickness'], insert.dxf.handle: ['rotation_angle_rad'],
                               label.dxf.handle: ['rotation_angle_rad'], point.dxf.handle: ['location']}
            self.assertEqual(comparison['differences'], [dict(reason='drawing_units_differ', dwg_insunits=4, dxf_insunits=6)] + [
                dict(handle=handle, reason='geometry_differs', fields=affected_fields[handle])
                for handle in sorted(affected_fields)
            ])
            stale_report = output / 'stale.json'
            with self.assertRaisesRegex(ValueError, 'differs from the verified revision artifact hashes'):
                run(source, stale_report, changed_dxf, expected_hashes=(original, file_hash(reference)))
            self.assertFalse(stale_report.exists())
