import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,validate_plan

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')
SOURCES=os.environ.get('BSA_TEST_HK_SOURCES')


@unittest.skipUnless(PYTHON and SOURCES,'requires isolated numerical runtime and official cached BEC')
class DerivedWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        runner=runpy.run_path(str(ROOT/'scripts/run_hk_three_phase_demo.py'))['run']
        cls.results=runner(Path(SOURCES)/'emsd-bec-2024.pdf',cls.root/'suite',Path(PYTHON),ifc_driven=True)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def stage(self,name):
        source=self.root/name
        shutil.copytree(self.root/'suite/conditional-pass',source,ignore=shutil.ignore_patterns('run','coverage'))
        return source,source/'regulated-plan.json'

    def test_actual_derived_projects_rules_and_blocking_scenarios(self):
        self.assertTrue(self.results['expected_behaviors_pass'])
        for row in self.results['scenarios']:
            directory=self.root/'suite'/row['scenario']/'run/power-flow'
            report=json.loads((directory/'derivation.json').read_text())
            p=json.loads((directory/'project.json').read_text())
            self.assertEqual([v['length_m'] for v in p['lines']],[40.,25.])
            self.assertEqual([v['baseline_length_m'] for v in report['changes']],[80,50])
            rules=json.loads((directory.parent/'hk-rule/phase-regulations.json').read_text())
            self.assertFalse(rules['design_accepted'])
            self.assertEqual(row['tasks']['hk-rule']['status'],'pass' if row['scenario']=='conditional-pass' else 'pending')
            self.assertFalse(row['design_accepted'])

    def test_missing_runtime_does_not_derive_or_check_rules(self):
        source,plan=self.stage('no-runtime')
        with patch('bsa.three_phase_ifc_project.run') as derive,patch('bsa.three_phase_regulations.run') as rules:
            result=execute(plan,source/'run')
        derive.assert_not_called();rules.assert_not_called()
        self.assertTrue(all(t['status']=='pending' for t in result['tasks'].values()))
        self.assertFalse((source/'run/power-flow').exists())

    def test_changed_derived_project_blocks_rules_and_drawing(self):
        from bsa.input_issues import blockers
        source,plan=self.stage('tamper');out=source/'run'
        def change(p,task_id):
            if task_id=='hk-rule':(out/'power-flow/project.json').write_text('{}',encoding='utf-8')
            return blockers(p,task_id)
        with patch('bsa.input_issues.blockers',side_effect=change),patch('bsa.three_phase_regulations.run') as rules,patch('bsa.three_phase_drawing.run') as drawing:
            result=execute(plan,out,three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        rules.assert_not_called();drawing.assert_not_called()
        self.assertEqual(result['tasks']['hk-rule']['status'],'fail')
        self.assertIn('producer artifacts changed',result['tasks']['hk-rule']['scope'])

    def test_failed_new_study_blocks_rules_and_drawing(self):
        source,plan=self.stage('failed-targets')
        p=json.loads((source/'project.json').read_text())
        for line in p['lines']:line['max_current_a']=1
        basis=source/'basis.md'
        with basis.open('a') as f:f.write('\nSynthetic current target failure: 1 A.\n')
        for record in p['sources'].values():record['sha256']=digest(basis)
        (source/'project.json').write_text(json.dumps(p),encoding='utf-8')
        with patch('bsa.three_phase_regulations.run') as rules,patch('bsa.three_phase_drawing.run') as drawing:
            result=execute(plan,source/'run',three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        rules.assert_not_called();drawing.assert_not_called()
        self.assertEqual(result['tasks']['power-flow']['status'],'fail')
        self.assertEqual(result['tasks']['hk-rule']['status'],'pending')

    def test_replacement_project_or_runtime_options_forbidden(self):
        source,plan=self.stage('replacement');p=json.loads(plan.read_text())
        p['tasks'][1]['project']='project.json';plan.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'replacement project'):validate_plan(plan)
        p['tasks'][1].pop('project');p['tasks'][0]['python']='untrusted.exe';plan.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'baseline project, IFC and binding only'):validate_plan(plan)

    def test_geometry_consumer_inherits_derived_project(self):
        source,plan=self.stage('geometry-consumer');p=json.loads(plan.read_text())
        p['tasks'].insert(1,dict(id='geometry',kind='three_phase_ifc',depends_on='power-flow',ifc='cable-fixture/cables.ifc',binding='cable-fixture/binding.json'))
        p['requirements'].append(dict(id='R5',passage='P001',quote=p['requirements'][0]['quote'],task='geometry',acceptance='Fresh saved geometry correspondence using derived project'))
        plan.write_text(json.dumps(p),encoding='utf-8')
        result=execute(plan,source/'run',three_phase_python=Path(PYTHON))
        self.assertEqual(result['tasks']['geometry']['status'],'pass')
        report=json.loads((source/'run/geometry/ifc-electrical-check.json').read_text())
        self.assertEqual([r['project_length_m'] for r in report['lines']],[40.,25.])
