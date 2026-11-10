import json
import shutil
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bsa.engine import ProjectError
from bsa.workflow import execute
from bsa.workflow_status import diagnose, water_runtime_failures
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class RuntimeRecoveryTests(unittest.TestCase):
    def test_policy_evidence_reaches_root_action_without_releasing_downstream(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            source_plan=ROOT/'examples/water-loop/plan.json'
            plan=json.loads(source_plan.read_text())
            for filename in ('brief.md','project.json'):
                shutil.copyfile(source_plan.parent/filename,root/filename)
            plan['tasks'].append(dict(id='review',kind='manual',requires_pass=['water'],description='Pending engineering review'))
            requirement=dict(plan['requirements'][0]);requirement.update(id='R_review',task='review')
            plan['requirements'].append(requirement)
            plan_path=root/'plan.json';plan_path.write_text(json.dumps(plan))
            def worker(*args,**kwargs):
                kwargs['stdout'].write(b'ImportError: An Application Control policy has blocked this file.')
                return SimpleNamespace(returncode=1)
            with patch('bsa.epanet.subprocess.run',side_effect=worker), patch('bsa.epanet.importlib.metadata.version',return_value='1.5.0'):
                result=execute(plan_path,root/'workflow')
            self.assertFalse(result['execution_pass'])
            self.assertEqual(result['tasks']['review']['status'],'pending')
            diagnosis=diagnose(plan_path,root/'workflow')
            action=diagnosis['actions'][0]
            self.assertEqual(action['runtime_failures'][0]['kind'],'application_control_block')
            self.assertIn('approved environment',action['next_action'])
            self.assertEqual(action['runtime_failures'][0]['evidence'],'water/worker.log')
            self.assertEqual(action['affected_tasks'],['water','review'])
            self.assertFalse(diagnosis['design_accepted'])
            (root/'workflow/water/worker.log').write_text('Changed evidence')
            with self.assertRaisesRegex(ProjectError,'stale execution evidence'):
                diagnose(plan_path,root/'workflow')

    def test_metadata_alone_cannot_assert_a_policy_block(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);(root/'water').mkdir()
            report=root/'water/water.json';log=root/'water/worker.log'
            report.write_text(json.dumps(dict(calculated_checks_pass=False,engine_error='Synthetic',
                engine_failure=dict(kind='application_control_block',evidence='worker.log'))))
            log.write_text('An unrelated numerical error')
            recorded=dict(artifact_hashes={'water/water.json':digest(report),'water/worker.log':digest(log)})
            with self.assertRaisesRegex(ProjectError,'differs from worker log'):
                water_runtime_failures(root,recorded,'water')
