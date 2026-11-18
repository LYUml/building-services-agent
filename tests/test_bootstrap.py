import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('bootstrap', Path(__file__).resolve().parents[1] / 'scripts/bootstrap.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class BootstrapTests(unittest.TestCase):
    def test_release_restore_allows_only_committed_export_exclusions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()

            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()

            git('init', '-q')
            (root / '.gitattributes').write_text('historical.dxf export-ignore\n', encoding='utf-8')
            historical = root / 'historical.dxf'
            historical.write_bytes(b'historical fixture')
            required = root / 'required.py'
            required.write_bytes(b'print(1)\n')
            git('add', '.')
            git('-c', 'user.name=BSA fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
            commit = git('rev-parse', 'HEAD')
            git('remote', 'add', 'origin', str(root))
            (root / '.bsa-release.json').write_text(json.dumps({'commit': commit}), encoding='utf-8')
            historical.unlink()
            with patch.object(setup, 'ROOT', root):
                setup.restore_source_git()
                self.assertFalse(historical.exists())
                required.unlink()
                with self.assertRaisesRegex(ValueError, 'differ from the release'):
                    setup.restore_source_git()
                self.assertFalse(required.exists())
                required.write_bytes(b'print(2)\n')
                with self.assertRaisesRegex(ValueError, 'differ from the release'):
                    setup.restore_source_git()
                self.assertEqual(required.read_bytes(), b'print(2)\n')

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
