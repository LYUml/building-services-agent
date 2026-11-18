from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from bsa.revit_file_metadata import inspect
from bsa.source_refs import file_hash


class RevitFileMetadataTests(unittest.TestCase):
    def test_report_allowlists_fields_and_preserves_unknown_status(self):
        with TemporaryDirectory() as directory:
            source = Path(directory).resolve() / 'fixture.rvt'
            source.write_bytes(b'synthetic adapter fixture')
            metadata = Mock(return_value=dict(revit_version=2027, workshared=None,
                                             single_user_cloud_model=False, username='test user',
                                             central_model_path='test private path'))
            reader = SimpleNamespace(__version__='0.25.0', RevitFile=Mock(return_value=SimpleNamespace(metadata=metadata)))
            with patch.dict('os.environ', BSA_PROJECT_ROOT=str(source.parent)), patch.dict(sys.modules, rvt=reader):
                result = inspect(source)
            metadata.assert_called_once_with(redact=True)
            self.assertEqual(result['source_sha256'], file_hash(source))
            self.assertEqual(result['revit_version'], 2027)
            self.assertIsNone(result['workshared'])
            self.assertIs(result['single_user_cloud_model'], False)
            self.assertNotIn('username', result)
            self.assertNotIn('central_model_path', result)
            self.assertFalse(result['native_revit_executed'])

    def test_report_rejects_a_model_changed_during_inspection(self):
        with TemporaryDirectory() as directory:
            source = Path(directory).resolve() / 'fixture.rvt'
            source.write_bytes(b'original model')

            def read_metadata(*, redact):
                source.write_bytes(b'replaced model')
                return dict(revit_version=2027, workshared=False)

            reader = SimpleNamespace(
                __version__='0.25.0',
                RevitFile=Mock(return_value=SimpleNamespace(metadata=read_metadata)),
            )
            with patch.dict('os.environ', BSA_PROJECT_ROOT=str(source.parent)), patch.dict(sys.modules, rvt=reader):
                with self.assertRaisesRegex(ValueError, 'changed during metadata inspection'):
                    inspect(source)
