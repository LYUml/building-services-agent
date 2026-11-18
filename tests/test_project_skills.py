import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa import project_skills as setup


class ProjectSkillsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.source = self.base / 'source'
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        self.skill = self.source / '.agents/skills/example/SKILL.md'
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text('---\nname: example\ndescription: test\n---\nRead docs/GUIDE.md.\n')
        self.python = self.source / '.bsa/venv/python'
        self.patch = patch.object(setup.workspace, 'ROOT', self.source)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def run_setup(self, **kwargs):
        return setup.install(self.project, self.python, **kwargs)

    def test_fresh_install_context_and_idempotent_rerun(self):
        self.assertEqual(self.run_setup()['changed_files'], 1)
        dest = self.project / '.agents/skills/example/SKILL.md'
        text = dest.read_text()
        self.assertTrue(text.startswith('---\nname: example'))
        self.assertIn(self.source.as_posix(), text)
        self.assertIn(self.python.as_posix(), text)
        before = dest.read_bytes()
        self.assertEqual(self.run_setup()['changed_files'], 0)
        self.assertEqual(dest.read_bytes(), before)

    def test_source_upgrade_replaces_only_unmodified_owned_skill(self):
        self.run_setup()
        self.skill.write_text(self.skill.read_text() + 'Updated method.\n')
        self.assertEqual(self.run_setup()['changed_files'], 1)
        self.assertIn('Updated method.', (self.project / '.agents/skills/example/SKILL.md').read_text())

    def test_user_edit_blocks_all_writes_and_preserves_manifest(self):
        self.run_setup()
        manifest = self.project / '.agents/bsa-skills.json'
        before = manifest.read_bytes()
        target = self.project / '.agents/skills/example/SKILL.md'
        target.write_text('user edit')
        new = self.source / '.agents/skills/aaa/SKILL.md'
        new.parent.mkdir()
        new.write_bytes(self.skill.read_bytes())
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.run_setup()
        self.assertEqual(target.read_text(), 'user edit')
        self.assertEqual(manifest.read_bytes(), before)
        self.assertFalse((self.project / '.agents/skills/aaa').exists())

    def test_unrelated_existing_skill_preserved_and_preflight_has_no_writes(self):
        other = self.project / '.agents/skills/custom/SKILL.md'
        other.parent.mkdir(parents=True)
        other.write_text('custom')
        self.run_setup(check_only=True)
        self.assertFalse((self.project / '.agents/bsa-skills.json').exists())
        self.run_setup()
        self.assertEqual(other.read_text(), 'custom')

    def test_protected_project_rejected(self):
        with patch.object(setup.workspace, 'protected', return_value=True):
            with self.assertRaisesRegex(ValueError, 'read-only'):
                self.run_setup()
        self.assertFalse((self.project / '.agents').exists())

    def test_source_project_is_read_only_noop(self):
        before = self.skill.read_bytes()
        result = setup.install(self.source, self.python)
        self.assertTrue(result['source_skills_in_place'])
        self.assertEqual(self.skill.read_bytes(), before)
        self.assertFalse((self.source / '.agents/bsa-skills.json').exists())

    def test_malformed_manifest_rejected(self):
        self.run_setup()
        manifest = self.project / '.agents/bsa-skills.json'
        data = json.loads(manifest.read_text())
        data['files']['../escape'] = 'x'
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'Invalid managed'):
            self.run_setup()
