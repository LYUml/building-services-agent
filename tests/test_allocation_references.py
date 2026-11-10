import hashlib
import tempfile
from pathlib import Path
import unittest
from bsa.air_allocation import reference_files


class AllocationReferenceTests(unittest.TestCase):
    def test_source_hash_and_changed_document(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'lecture.pdf';source.write_bytes(b'Synthetic source fixture')
            project=dict(references={'lecture.pdf':hashlib.sha256(source.read_bytes()).hexdigest()})
            self.assertEqual(set(reference_files(root/'allocation.json',project)),{source.resolve()})
            source.write_bytes(b'Changed source')
            with self.assertRaisesRegex(ValueError,'source hash mismatch'):reference_files(root/'allocation.json',project)

    def test_optional_and_invalid_source_paths(self):
        self.assertEqual(reference_files(Path('allocation.json'),{}),{})
        with self.assertRaisesRegex(ValueError,'Relative'):reference_files(Path('allocation.json'),dict(references={str(Path.cwd()/'source.pdf'):'hash'}))
