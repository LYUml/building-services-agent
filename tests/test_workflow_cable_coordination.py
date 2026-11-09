import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.engine import ProjectError
from bsa.workflow import execute,three_phase_model_bindings,three_phase_rule_bindings,inventory_source_bindings

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class ElectricalInventoryIdentityTests(unittest.TestCase):
    def test_electrical_input_readers_use_explicit_bytes_not_numerical_producer(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);(root/'a.ifc').write_text('identity A');(root/'copy.ifc').write_text('identity A');(root/'b.ifc').write_text('identity B')
            for kind in ('three_phase_ifc_project','three_phase_ifc','three_phase_topology','three_phase_bend_limits','three_phase_coordination'):
                with self.subTest(kind=kind):
                    reader=dict(id='consumer',kind=kind,ifc='a.ifc',requires_pass=['inventory'])
                    if kind!='three_phase_ifc_project':reader['depends_on']='study'
                    tasks=[dict(id='inventory',kind='ifc_query',ifc='a.ifc'),dict(id='study',kind='three_phase'),reader]
                    self.assertEqual(len(inventory_source_bindings(tasks,root)),1)
                    reader['ifc']='copy.ifc';self.assertEqual(len(inventory_source_bindings(tasks,root)),1)
                    reader['ifc']='b.ifc'
                    with self.assertRaisesRegex(ProjectError,'different model'):inventory_source_bindings(tasks,root)


@unittest.skipUnless(PYTHON,'requires isolated numerical runtime')
class ElectricalCoordinationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        runner=runpy.run_path(str(ROOT/'scripts/run_cable_coordination_demo.py'))['run']
        cls.result=runner(cls.root/'suite',Path(PYTHON))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def stage(self,name,case='clear'):
        source=self.root/name;shutil.copytree(self.root/'suite'/case,source,ignore=shutil.ignore_patterns('run'))
        return source,source/'plan.json'

    def test_actual_clear_near_and_overlap_scenarios(self):
        self.assertTrue(self.result['expected_behaviors_pass'])
        for row in self.result['scenarios']:
            self.assertEqual(row['tasks']['coordination']['status'],'pass' if row['scenario']=='clear' else 'fail')
            self.assertEqual(len(row['model_bindings']),2);self.assertFalse(row['design_accepted'])

    def test_missing_runtime_blocks_coordination(self):
        source,plan=self.stage('no-runtime')
        with patch('bsa.three_phase_coordination.run') as check:
            r=execute(plan,source/'run')
        check.assert_not_called();self.assertEqual(r['tasks']['coordination']['status'],'pending')

    def test_unrelated_model_and_study_gate_rejected(self):
        source,plan=self.stage('mismatch');p=json.loads(plan.read_text())
        (source/'other.ifc').write_bytes((source/'combined/model.ifc').read_bytes()+b'\n');p['tasks'][1]['ifc']='other.ifc'
        with self.assertRaisesRegex(ProjectError,'different IFC or cable binding'):three_phase_model_bindings(source,p['tasks'])
        p=json.loads(plan.read_text());p['tasks'].insert(2,dict(id='other',kind='three_phase',project='project.json'));p['tasks'][3]['depends_on']='other'
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(p['tasks'])

    def test_overlap_blocks_before_drawing_adapter(self):
        source,plan=self.stage('overlap-block','material-overlap')
        with patch('bsa.three_phase_drawing.run') as draw:
            r=execute(plan,source/'run',three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called();self.assertEqual(r['tasks']['coordination']['status'],'fail')
        self.assertFalse((source/'run/drawing').exists())

    def test_changed_nested_clash_result_blocks_drawing(self):
        from bsa.input_issues import blockers
        source,plan=self.stage('tamper');out=source/'run'
        def alter(p,task_id):
            if task_id=='drawing':(out/'coordination/clash/clash.json').write_text('{}',encoding='utf-8')
            return blockers(p,task_id)
        with patch('bsa.input_issues.blockers',side_effect=alter),patch('bsa.three_phase_drawing.run') as draw:
            r=execute(plan,out,three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called();self.assertEqual(r['tasks']['drawing']['status'],'fail')
        self.assertIn('artifacts changed',r['tasks']['drawing']['scope'])
