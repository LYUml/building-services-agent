import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bsa.project_start import start
from bsa.modules import verify_result
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.workspace import allowed,project_root


class ProjectWorkspaceTests(unittest.TestCase):
    def test_external_intake_requires_host_selection_and_preserves_blockers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();brief=root/'brief.md';brief.write_text('Calculate ventilation and retain missing inputs.')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaises(ValueError):start(brief,root/'denied')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(root)}):
                result=start(brief,root/'project');inventory=root/'project'/result['requirements_module']['result']
                self.assertEqual(verify_result(inventory)['execution']['status'],'completed')
                plan=root/'project/plan.json';run=root/'execution';r=execute(plan,run,requirements_result=inventory)
                self.assertTrue(verify(run)['integrity_pass']);context(plan,run)
                self.assertTrue(all(t['status']=='pending' for t in r['tasks'].values()))
                self.assertFalse(allowed(root.parent/'unselected-sibling'))
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaises(ValueError):verify_result(inventory)

    def test_relative_volume_root_and_missing_host_roots_reject(self):
        for value in ['relative-project',str(Path.cwd().anchor),str(Path(tempfile.gettempdir())/'absent-bsa-workspace-control')]:
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':value}):
                with self.assertRaises(ValueError):project_root()
