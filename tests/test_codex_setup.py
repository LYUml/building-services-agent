import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tomllib
from bsa import codex_setup as setup


class LocalSetupTests(unittest.TestCase):
    def test_ambiguous_updated_flag_and_normalizing_writer_preserve_original(self):
        import tomlkit
        with tempfile.TemporaryDirectory() as folder:
            root,python=self.fixture(folder);new=root/'new-python.txt';new.write_text('Never executed')
            with patch.object(setup.workspace,'ROOT',root),patch.object(setup.workspace,'project_root',return_value=None):
                setup.install(python);target=root/'.codex/config.toml';original=target.read_bytes()
                document=tomlkit.parse(original.decode());document['mcp_servers'][setup.SERVER]['args'].extend(['--autocad','--pdftoppm'])
                target.write_bytes(tomlkit.dumps(document).encode());malformed=target.read_bytes()
                with self.assertRaisesRegex(ValueError,'Ambiguous'):setup.install(new,autocad=new,refresh=True)
                self.assertEqual(target.read_bytes(),malformed)
                target.write_bytes(original)
                with patch.object(tomlkit,'dumps',return_value='# normalized\n'+original.decode()):
                    with self.assertRaisesRegex(ValueError,'roundtripped unchanged'):setup.install(new,refresh=True)
                self.assertEqual(target.read_bytes(),original)

    def test_refresh_keeps_user_controls_and_unspecified_runtimes(self):
        import tomlkit
        with tempfile.TemporaryDirectory() as folder:
            root,python=self.fixture(folder);new=root/'new-python.txt';new.write_text('Never executed')
            with patch.object(setup.workspace,'ROOT',root),patch.object(setup.workspace,'project_root',return_value=None):
                setup.install(python,pdftoppm=python);target=root/'.codex/config.toml'
                document=tomlkit.parse(target.read_text());table=document['mcp_servers'][setup.SERVER]
                table['enabled']=False;table['tool_timeout_sec']=333;table['default_tools_approval_mode']='prompt';table['env']['UNRELATED_SETTING']='preserve'
                prefix='# user comment\nmodel = "preserve"\n';target.write_text(prefix+tomlkit.dumps(document));before=target.read_bytes()
                self.assertTrue(setup.install(new,autocad=new,refresh=True)['changed'])
                result=tomllib.loads(target.read_text());table=result['mcp_servers'][setup.SERVER]
                self.assertTrue(target.read_bytes().startswith(before.split(b'[mcp_servers',1)[0]));self.assertFalse(table['enabled']);self.assertEqual(table['tool_timeout_sec'],333);self.assertEqual(table['default_tools_approval_mode'],'prompt');self.assertEqual(table['env']['UNRELATED_SETTING'],'preserve')
                self.assertEqual(table['command'],new.as_posix());self.assertEqual(table['args'][table['args'].index('--pdftoppm')+1],python.as_posix())
                self.assertEqual((target.parent/'config.before-building-services.toml').read_bytes(),before)
                self.assertFalse(setup.install(new,refresh=True)['changed'])
                setup.install(python,refresh=True);self.assertEqual(len(list(target.parent.glob('config.before-building-services*.toml'))),2)

    def test_failed_atomic_replace_keeps_original_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            root,python=self.fixture(folder);target=root/'config.toml';original=b'# original\n';target.write_bytes(original)
            with patch.object(setup.os,'replace',side_effect=OSError('Synthetic replacement failure')):
                with self.assertRaises(OSError):setup.write_config(target,original,b'# replacement\n')
            self.assertEqual(target.read_bytes(),original);self.assertEqual(list(root.glob('.bsa-config-*')),[])
            self.assertEqual((root/'config.before-building-services.toml').read_bytes(),original)

    def test_unknown_launcher_and_wrong_library_pin_keep_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root,python=self.fixture(folder);new=root/'other-python.txt';new.write_text('Never executed')
            with patch.object(setup.workspace,'ROOT',root),patch.object(setup.workspace,'project_root',return_value=None):
                setup.install(python);target=root/'.codex/config.toml';before=target.read_bytes()
                with patch.object(setup.importlib.metadata,'version',return_value='0'):
                    with self.assertRaisesRegex(ValueError,'Pinned tomlkit'):setup.install(new,refresh=True)
                self.assertEqual(target.read_bytes(),before)
                target.write_text('[mcp_servers.building_services]\ncommand="custom"\nargs=["custom"]\n');before=target.read_bytes()
                with self.assertRaisesRegex(ValueError,'known BSA module'):setup.install(new,refresh=True)
                self.assertEqual(target.read_bytes(),before)

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
