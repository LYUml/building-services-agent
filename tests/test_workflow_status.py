import json
from pathlib import Path
import tempfile
import unittest

from bsa.engine import ProjectError
from bsa.workflow import execute
from bsa.workflow_status import diagnose

ROOT = Path(__file__).resolve().parents[1]


class WorkflowStatusTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'runs').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)/'run'
        self.plan = ROOT/'examples/shared-lighting-plan.json'
        execute(self.plan, self.run)

    def test_missing_engine_explains_dependency_and_manual_work_separately(self):
        result = diagnose(self.plan, self.run)
        rows = {r['id']: r for r in result['tasks']}
        self.assertEqual(rows['native']['blocked_by'], ['shared'])
        self.assertEqual(rows['native']['upstream_action_tasks'], ['shared'])
        self.assertEqual(rows['shared']['upstream_action_tasks'], ['shared'])
        self.assertIn('Radiance', rows['shared']['recorded_scope'])
        self.assertEqual(rows['native']['requirement_ids'], ['R2'])
        self.assertIn('review', rows['review']['next_action'])
        self.assertFalse(result['execution_pass'])
        self.assertFalse(result['design_accepted'])

    def test_failed_water_producer_traces_shared_roots_through_multiple_levels(self):
        from unittest.mock import patch
        plan = ROOT/'examples/water-riser/coupled-plan.json'
        run = Path(self.temp.name)/'coupled'
        # Only the water producer is fault-injected. Electrical calculations,
        # source validation, dependency dispatch and integrity checks execute.
        with patch('bsa.network_model_design.run',side_effect=ProjectError('controlled water design failure')):
            execute(plan,run)
        rows = {r['id']:r for r in diagnose(plan,run)['tasks']}
        self.assertEqual(rows['electrical']['status'],'pass')
        self.assertEqual(rows['electrical']['upstream_action_tasks'],[])
        self.assertTrue(rows['electrical']['evidence'])
        self.assertEqual(rows['coupled']['blocked_by'],['pump','water'])
        self.assertEqual(rows['coupled']['upstream_action_tasks'],['water'])
        self.assertEqual(rows['coupled-drawing']['blocked_by'],['coupled'])
        self.assertEqual(rows['coupled-drawing']['upstream_action_tasks'],['water'])
        self.assertEqual(rows['water']['status'],'fail')
        self.assertIn('controlled water design failure',rows['water']['recorded_scope'])
        self.assertEqual(rows['coupled-drawing']['evidence'],[])

    def test_passing_child_with_pending_parent_is_rejected(self):
        path = self.run/'workflow.json'
        report = json.loads(path.read_text())
        report['tasks']['native']['status'] = 'pass'
        for requirement in report['requirements']:
            if requirement['task'] == 'native':
                requirement['execution_status'] = 'pass'
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ProjectError, 'nonpassing dependencies'):
            diagnose(self.plan, self.run)

    def test_changed_recorded_artifact_cannot_supply_actions(self):
        path = self.run/'workflow.json'
        report = json.loads(path.read_text())
        report['artifact_hashes']['shared/missing.json'] = '0'*64
        for requirement in report['requirements']:
            if requirement['task'] == 'shared':
                requirement['evidence'] = ['shared/missing.json']
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ProjectError, 'stale execution evidence'):
            diagnose(self.plan, self.run)
