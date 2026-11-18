from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from zipfile import ZipFile

from bsa.ifc_port_bcf import verify, write
from bsa.source_refs import file_hash


@unittest.skipUnless(find_spec('bcf'), 'requires the optional BCF runtime')
class IfcPortBcfTests(unittest.TestCase):
    def test_rejects_topic_folder_with_different_guid(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            root = Path(temporary)
            source = root / 'source.ifc'
            source.write_bytes(b'stand-in for the source hash in verifier tests')
            report = {
                'source_sha256': file_hash(source),
                'ports': [{'guid': 'port', 'origin_m': None, 'owner_evidence': []}],
                'connection_gaps': {'tolerance_m': 0.001, 'separated_relationships': [],
                                    'unavailable_relationships': []},
                'connection_ownership': {'conflicting_ports': ['port']},
            }
            original = root / 'original.bcf'
            result = write(report, source, original)
            self.assertEqual(result['topics'], 1)
            self.assertTrue(result['archive_tolerance_bound'])
            report['connection_gaps']['tolerance_m'] = 0.002
            with self.assertRaisesRegex(ValueError, 'does not match the supplied port gap tolerance'):
                verify(report, original)
            report['connection_gaps']['tolerance_m'] = 0.001
            changed = root / 'changed.bcf'
            different_guid = str(uuid4())
            with ZipFile(original) as saved, ZipFile(changed, 'x') as modified:
                for name in saved.namelist():
                    _, separator, member = name.partition('/')
                    modified.writestr(f'{different_guid}/{member}' if separator else name, saved.read(name))

            with self.assertRaisesRegex(ValueError, 'topic directory differs from its markup GUID'):
                verify(report, changed)
