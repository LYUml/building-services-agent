import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('bootstrap', Path(__file__).resolve().parents[1] / 'scripts/bootstrap.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class BootstrapTests(unittest.TestCase):
    def test_protected_root_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'polyu_bse3124'
            with self.assertRaisesRegex(ValueError, 'read-only'):
                setup.validate_root(root)
            self.assertFalse(root.exists())

    def test_unknown_owned_directory_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / '.bsa').mkdir()
            (root / '.bsa' / 'mine').write_text('keep')
            with self.assertRaisesRegex(ValueError, 'not owned'):
                setup.validate_root(root)
            self.assertEqual((root / '.bsa' / 'mine').read_text(), 'keep')

    def test_zip_without_manifest_cannot_select_remote(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(setup, 'ROOT', Path(folder)):
            with self.assertRaisesRegex(ValueError, 'official source'):
                setup.restore_source_git()
            self.assertFalse((Path(folder) / '.git').exists())

    def test_git_clone_does_not_reset_user_changes(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(setup, 'ROOT', Path(folder)), patch.object(setup, 'run') as run:
            (Path(folder) / '.git').mkdir()
            setup.restore_source_git()
            run.assert_not_called()

    def test_manifest_commit_cannot_inject_arguments(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(setup, 'ROOT', Path(folder)), patch.object(setup, 'run') as run:
            (Path(folder) / '.bsa-release.json').write_text('{"commit":"--upload-pack=evil"}')
            with self.assertRaisesRegex(ValueError, 'Invalid release commit'):
                setup.restore_source_git()
            run.assert_not_called()
