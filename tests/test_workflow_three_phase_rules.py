import copy
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from bsa.engine import ProjectError
from bsa.workflow import execute,three_phase_rule_bindings,validate_plan
from bsa.delivery import context

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')
SOURCES=os.environ.get('BSA_TEST_HK_SOURCES')


class StudyBindingTests(unittest.TestCase):
    def test_direct_and_transitive_wrong_study_gates_rejected(self):
        tasks=[dict(id='a',kind='three_phase'),dict(id='rule',kind='three_phase_regulations',depends_on='a'),
            dict(id='b',kind='three_phase'),dict(id='proxy',kind='manual',requires_pass=['rule']),
            dict(id='drawing',kind='three_phase_drawing',depends_on='b',requires_pass=['proxy'])]
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(tasks)
        tasks[-1]['requires_pass']=['rule']
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(tasks)
        tasks[-1]['depends_on']='a'
        self.assertEqual(three_phase_rule_bindings(tasks),[dict(check='rule',consumer='drawing',study_producer='a')])


@unittest.skipUnless(PYTHON and SOURCES,'requires explicit isolated runtime and official cache')
class RuleWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)/'demo'
        runner=runpy.run_path(str(ROOT/'scripts/run_hk_three_phase_demo.py'))['run']
        cls.result=runner(Path(SOURCES)/'emsd-bec-2024.pdf',cls.root,Path(PYTHON))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_actual_scenarios_keep_missing_exceeded_and_full_acceptance_pending(self):
        self.assertTrue(self.result['expected_behaviors_pass'])
        for item in self.result['scenarios']:
            self.assertEqual(item['tasks']['power-flow']['status'],'pass')
            self.assertEqual(item['tasks']['hk-rule']['status'],'pass' if item['scenario']=='conditional-pass' else 'pending')
            self.assertEqual(item['tasks']['drawing']['status'],'pending')
            self.assertFalse(item['design_accepted'])
            self.assertEqual(item['selected_topic_gaps'],['partial_rule_coverage'])

    def test_replacement_project_and_changed_binding_record_rejected(self):
        source=self.root/'conditional-pass';plan=source/'regulated-plan.json'
        original=plan.read_bytes();p=json.loads(original)
        p['tasks'][1]['project']='project.json';plan.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'replacement project'):validate_plan(plan)
        plan.write_bytes(original)
        report=source/'run/workflow.json';original_report=report.read_bytes();r=json.loads(original_report)
        r['three_phase_source_bindings']=[];report.write_text(json.dumps(r),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'source bindings differ'):context(plan,source/'run')
        report.write_bytes(original_report)

    def test_changed_rule_artifact_stops_before_cad_call(self):
        from bsa.input_issues import blockers
        source=self.root/'conditional-pass';out=source/'tampered-rule-run'
        def altered(plan,task_id):
            if task_id=='drawing':(out/'hk-rule/phase-regulations.json').write_text('{}',encoding='utf-8')
            return blockers(plan,task_id)
        with patch('bsa.input_issues.blockers',side_effect=altered),patch('bsa.three_phase_drawing.run') as draw:
            r=execute(source/'regulated-plan.json',out,three_phase_python=Path(PYTHON),graphviz=Path('unused.exe'),autocad=Path('unused.exe'))
        draw.assert_not_called();self.assertEqual(r['tasks']['drawing']['status'],'fail')
        self.assertIn('rule artifacts changed',r['tasks']['drawing']['scope'])
        self.assertFalse((out/'drawing').exists())


if __name__=='__main__':unittest.main()
