import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.engine import ProjectError
from bsa.workflow import execute,validate_plan,three_phase_rule_bindings,three_phase_model_bindings

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


@unittest.skipUnless(PYTHON,'requires isolated numerical runtime')
class BendReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        runner=runpy.run_path(str(ROOT/'scripts/run_cable_bend_limits_demo.py'))['run']
        cls.result=runner(cls.root/'suite',Path(PYTHON))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def stage(self,name,case='conditional-pass'):
        source=self.root/name;shutil.copytree(self.root/'suite'/case,source,ignore=shutil.ignore_patterns('run'))
        return source,source/'plan.json'

    def test_actual_source_bound_scenarios_and_identity_records(self):
        self.assertTrue(self.result['expected_behaviors_pass'])
        for row in self.result['scenarios']:
            expected={'conditional-pass':'pass','inside-radius-too-small':'fail','unknown-radius-reference':'pending'}[row['scenario']]
            self.assertEqual(row['tasks']['bend-check']['status'],expected)
            self.assertEqual(row['tasks']['drawing']['status'],'pending')
            self.assertEqual(len(row['model_bindings']),2)
            self.assertFalse(row['design_accepted'])

    def test_missing_runtime_blocks_before_limit_adapter(self):
        source,plan=self.stage('no-runtime')
        with patch('bsa.cable_bend_limits.run') as check:
            r=execute(plan,source/'run')
        check.assert_not_called();self.assertEqual(r['tasks']['bend-check']['status'],'pending')

    def test_other_study_and_model_gate_rejected(self):
        source,plan=self.stage('different-model');p=json.loads(plan.read_text())
        other=source/'alternate.ifc';other.write_bytes((source/'cable-fixture/cables.ifc').read_bytes()+b'\n')
        p['tasks'][1]['ifc']='alternate.ifc'
        with self.assertRaisesRegex(ProjectError,'different IFC or cable binding'):three_phase_model_bindings(source,p['tasks'])
        p=json.loads(plan.read_text());p['tasks'].insert(2,dict(id='other',kind='three_phase',project='project.json'))
        p['tasks'][3]['depends_on']='other'
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(p['tasks'])

    def test_replacement_project_forbidden(self):
        source,plan=self.stage('replacement');p=json.loads(plan.read_text());p['tasks'][1]['project']='project.json'
        plan.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'replacement project'):validate_plan(plan)

    def test_failed_limit_blocks_before_native_drawing_call(self):
        source,plan=self.stage('failure-block','inside-radius-too-small')
        with patch('bsa.three_phase_drawing.run') as draw:
            r=execute(plan,source/'run',three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called();self.assertEqual(r['tasks']['bend-check']['status'],'fail')
        self.assertEqual(r['tasks']['drawing']['status'],'pending');self.assertFalse((source/'run/drawing').exists())

    def test_changed_limit_result_blocks_drawing(self):
        from bsa.input_issues import blockers
        source,plan=self.stage('changed-result');out=source/'run'
        def change(p,task_id):
            if task_id=='drawing':(out/'bend-check/bend-limits.json').write_text('{}',encoding='utf-8')
            return blockers(p,task_id)
        with patch('bsa.input_issues.blockers',side_effect=change),patch('bsa.three_phase_drawing.run') as draw:
            r=execute(plan,out,three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called();self.assertEqual(r['tasks']['drawing']['status'],'fail')
        self.assertIn('artifacts changed',r['tasks']['drawing']['scope'])
