import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tomllib
from bsa import codex_setup as setup


class LocalSetupTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder).resolve()/'agent';root.mkdir();(root/'runs').mkdir();python=root/'fictional-python.txt';python.write_text('Configuration control; never executed')
        return root,python

    def test_append_preserves_existing_bytes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root,python=self.fixture(folder);(root/'.codex').mkdir();target=root/'.codex/config.toml';original=b'# user setting\nmodel = "preserved"\n';target.write_bytes(original)
            with patch.object(setup.workspace,'ROOT',root),patch.object(setup.workspace,'project_root',return_value=None):
                self.assertTrue(setup.install(python)['changed']);self.assertTrue(target.read_bytes().startswith(original))
                data=tomllib.loads(target.read_text());self.assertEqual(data['mcp_servers'][setup.SERVER]['env']['BSA_PROJECT_ROOT'],(root/'runs').as_posix())
                self.assertEqual((target.parent/'config.before-building-services.toml').read_bytes(),original)
                self.assertFalse(setup.install(python)['changed'])
                with self.assertRaisesRegex(ValueError,'differs'):setup.install(python,autocad=python)

    def test_explicit_external_workspace_stays_separate_and_history_rejects(self):
        with tempfile.TemporaryDirectory() as folder:
            root,python=self.fixture(folder);project=root.parent/'course';project.mkdir()
            with patch.object(setup.workspace,'ROOT',root),patch.object(setup.workspace,'project_root',return_value=project):
                setup.install(python);data=tomllib.loads((project/'.codex/config.toml').read_text());self.assertEqual(data['mcp_servers'][setup.SERVER]['env']['BSA_PROJECT_ROOT'],project.as_posix());self.assertFalse((root/'.codex').exists())
            history=root.parent/'polyu_bse3124';history.mkdir()
            with patch.object(setup.workspace,'ROOT',root),patch.object(setup.workspace,'project_root',return_value=history):
                with self.assertRaisesRegex(ValueError,'read-only'):setup.install(python)
            self.assertEqual(list(history.iterdir()),[])

    def test_bad_toml_and_missing_runtime_preserve_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root,python=self.fixture(folder);(root/'.codex').mkdir();target=root/'.codex/config.toml';target.write_text('[broken')
            with patch.object(setup.workspace,'ROOT',root),patch.object(setup.workspace,'project_root',return_value=None):
                with self.assertRaises(tomllib.TOMLDecodeError):setup.install(python)
                self.assertEqual(target.read_text(),'[broken')
                with self.assertRaisesRegex(ValueError,'Python'):setup.settings(root/'missing')
