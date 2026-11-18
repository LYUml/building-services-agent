import hashlib
from importlib.util import find_spec
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from bsa.delivery_archive import verify_archive


RUNS = Path(__file__).resolve().parents[1] / 'runs'
MEMBER = 'Drawings/Final.dwg'
DATA = b'synthetic drawing bytes'


class DeliveryArchiveTests(unittest.TestCase):
    def test_file_cannot_be_a_parent_even_with_matching_hashes(self):
        with TemporaryDirectory(dir=RUNS) as temporary:
            root = Path(temporary)
            archive, manifest = root / 'release.zip', root / 'pins.json'
            names = ('drawings', MEMBER)
            with ZipFile(archive, 'x') as bundle:
                for name in names:
                    bundle.writestr(name, DATA)
            manifest.write_text(json.dumps({name: hashlib.sha256(DATA).hexdigest() for name in names}),
                                encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'both a file and a parent directory'):
                verify_archive(archive, manifest)

    def test_archive_checks_inventory_paths_and_content(self):
        with TemporaryDirectory(dir=RUNS) as temporary:
            root = Path(temporary)
            archive, manifest = root / 'release.zip', root / 'pins.json'
            manifest.write_text(json.dumps({MEMBER: hashlib.sha256(DATA).hexdigest()}), encoding='utf-8')
            cases = [
                ([(MEMBER, DATA)], None),
                ([(MEMBER, b'changed')], 'member hash mismatch'),
                ([(MEMBER, DATA), ('extra.txt', DATA)], 'inventory differs'),
                ([(MEMBER, DATA), (MEMBER.lower(), DATA)], 'Duplicate ZIP member'),
                ([('../Final.dwg', DATA)], 'Invalid delivery member path'),
                ([], 'inventory differs'),
            ]
            for files, error in cases:
                with self.subTest(error=error, files=[name for name, _ in files]):
                    with ZipFile(archive, 'w') as bundle:
                        for name, data in files:
                            bundle.writestr(name, data)
                    if error is None:
                        self.assertEqual(verify_archive(archive, manifest)['verified_members'], 1)
                    else:
                        with self.assertRaisesRegex(ValueError, error):
                            verify_archive(archive, manifest)
            self.assertCountEqual(list(root.iterdir()), [archive, manifest])


@unittest.skipUnless(find_spec('mcp'), 'requires the MCP SDK')
class DeliveryArchiveMcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_and_stdio_return_same_result(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with TemporaryDirectory(dir=RUNS) as temporary:
            root = Path(temporary)
            archive, manifest = root / 'release.zip', root / 'pins.json'
            with ZipFile(archive, 'x') as bundle:
                bundle.writestr(MEMBER, DATA)
            manifest.write_text(json.dumps({MEMBER: hashlib.sha256(DATA).hexdigest()}), encoding='utf-8')
            result = subprocess.check_output(
                [sys.executable, '-m', 'bsa.cli', 'delivery', 'verify-archive', str(archive), str(manifest)],
                timeout=30,
            )
            params = StdioServerParameters(command=sys.executable, args=['-m', 'bsa.mcp_server'],
                                           env={**os.environ, 'BSA_PROJECT_ROOT': str(root)})
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    args = {'archive': archive.name, 'manifest': manifest.name}
                    good = await session.call_tool('bsa_verify_delivery_archive', args)
                    self.assertFalse(good.isError, good.content)
                    self.assertEqual(good.structuredContent, json.loads(result))
                    archive.write_bytes(b'invalid ZIP file')
                    bad = await session.call_tool('bsa_verify_delivery_archive', args)
                    self.assertTrue(bad.isError)
                    self.assertIn('Cannot read delivery ZIP', str(bad.content))
