import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
import ifcopenshell
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,three_phase_rule_bindings

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class ElectricalTopologyWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        source=ROOT/'examples/three-phase-network'
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(source/'project.json',source/'cable-geometry.json',cls.root/'cables','extrusion')
        attach=runpy.run_path(str(ROOT/'scripts/author_three_phase_topology_fixture.py'))['run']
        attach(source/'project.json',cls.root/'cables/cables.ifc',cls.root/'cables/binding.json',source/'topology-geometry.json',cls.root/'connected')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.source=self.root/self._testMethodName
        shutil.copytree(ROOT/'examples/three-phase-network',self.source)
        shutil.copytree(self.root/'connected',self.source/'cable-fixture')
        self.plan=self.source/'ifc-plan.json'
        self.p=json.loads((self.source/'ifc-plan.json.in').read_text())
        self.p['tasks'][1].update(kind='three_phase_topology',ifc='cable-fixture/connected-cables.ifc',topology='cable-fixture/topology-binding.json')
        self.plan.write_text(json.dumps(self.p),encoding='utf-8')

    def test_missing_runtime_blocks_topology(self):
        with patch('bsa.three_phase_topology.run') as check:
            result=execute(self.plan,self.source/'run')
        check.assert_not_called();self.assertEqual(result['tasks']['geometry']['status'],'pending')

    def test_wrong_numerical_producer_gate_rejected(self):
        tasks=self.p['tasks'];tasks.insert(2,dict(id='other',kind='three_phase',project='project.json'))
        tasks[3]['depends_on']='other'
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(tasks)

    @unittest.skipUnless(PYTHON,'requires isolated numerical runtime')
    def test_actual_passing_study_and_native_topology(self):
        r=execute(self.plan,self.source/'run',three_phase_python=Path(PYTHON))
        self.assertEqual(r['tasks']['geometry']['status'],'pass')
        self.assertFalse(r['design_accepted'])
        self.assertEqual(r['three_phase_source_bindings'],[dict(check='geometry',consumer='drawing',study_producer='study')])

    @unittest.skipUnless(PYTHON,'requires isolated numerical runtime')
    def test_disconnected_graph_blocks_drawing(self):
        path=self.source/'cable-fixture/connected-cables.ifc';m=ifcopenshell.open(str(path))
        m.remove(m.by_type('IfcRelConnectsPorts')[0]);m.write(str(path))
        for name in ('binding.json','topology-binding.json'):
            file=self.source/'cable-fixture'/name;p=json.loads(file.read_text());p['ifc_sha256']=digest(path)
            file.write_text(json.dumps(p),encoding='utf-8')
        with patch('bsa.three_phase_drawing.run') as draw:
            r=execute(self.plan,self.source/'run',three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called();self.assertEqual(r['tasks']['geometry']['status'],'fail')
        self.assertEqual(r['tasks']['drawing']['status'],'pending')

    @unittest.skipUnless(PYTHON,'requires isolated numerical runtime')
    def test_changed_topology_evidence_blocks_drawing(self):
        from bsa.input_issues import blockers
        out=self.source/'run'
        def altered(p,task_id):
            if task_id=='drawing':(out/'geometry/topology.json').write_text('{}',encoding='utf-8')
            return blockers(p,task_id)
        with patch('bsa.input_issues.blockers',side_effect=altered),patch('bsa.three_phase_drawing.run') as draw:
            r=execute(self.plan,out,three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called();self.assertEqual(r['tasks']['drawing']['status'],'fail')
