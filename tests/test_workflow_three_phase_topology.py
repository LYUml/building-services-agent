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
from bsa.workflow import execute,three_phase_rule_bindings,three_phase_model_bindings,validate_plan

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

    def alternate(self,change_model=True):
        folder=self.source/'cable-fixture';path=folder/'alternate.ifc'
        m=ifcopenshell.open(str(folder/'connected-cables.ifc'))
        if change_model:m.by_type('IfcElectricDistributionBoard')[0].Name+=' alternate revision'
        if change_model:m.write(str(path))
        else:shutil.copyfile(folder/'connected-cables.ifc',path)
        for old,new in (('binding.json','alternate-binding.json'),('topology-binding.json','alternate-topology.json')):
            data=json.loads((folder/old).read_text());data['ifc_sha256']=digest(path)
            (folder/new).write_text(json.dumps(data),encoding='utf-8')
        return path

    def derived(self):
        self.p['tasks'][0].update(kind='three_phase_ifc_project',ifc='cable-fixture/connected-cables.ifc',binding='cable-fixture/binding.json')

    def test_valid_same_geometry_alternate_model_cannot_borrow_derived_study(self):
        from bsa.three_phase_topology import inspect
        path=self.alternate();folder=path.parent
        self.assertTrue(inspect(self.source/'project.json',path,folder/'alternate-binding.json',folder/'alternate-topology.json')['logical_graph_correspondence_pass'])
        self.derived()
        self.p['tasks'][1].update(ifc='cable-fixture/alternate.ifc',binding='cable-fixture/alternate-binding.json',topology='cable-fixture/alternate-topology.json')
        self.plan.write_text(json.dumps(self.p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'different IFC or cable binding'):validate_plan(self.plan)

    def test_different_role_binding_is_not_same_model_identity(self):
        self.derived();file=self.source/'cable-fixture/alternate-binding.json'
        data=json.loads((file.parent/'binding.json').read_text());data['source']['locator']+=' Revised mapping basis.'
        file.write_text(json.dumps(data),encoding='utf-8')
        self.p['tasks'][1]['binding']='cable-fixture/alternate-binding.json'
        self.plan.write_text(json.dumps(self.p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'different IFC or cable binding'):validate_plan(self.plan)

    def test_byte_identical_model_and_binding_copies_allowed(self):
        self.derived();folder=self.source/'cable-fixture'
        shutil.copyfile(folder/'connected-cables.ifc',folder/'identical.ifc')
        shutil.copyfile(folder/'binding.json',folder/'identical-binding.json')
        self.p['tasks'][1].update(ifc='cable-fixture/identical.ifc',binding='cable-fixture/identical-binding.json')
        self.plan.write_text(json.dumps(self.p),encoding='utf-8')
        validate_plan(self.plan)
        records=three_phase_model_bindings(self.source,self.p['tasks'])
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]['ifc_sha256'],records[1]['ifc_sha256'])

    def test_drawing_cannot_combine_other_model_geometry_and_topology_gates(self):
        self.alternate()
        self.p['tasks'][1].update(ifc='cable-fixture/alternate.ifc',binding='cable-fixture/alternate-binding.json',topology='cable-fixture/alternate-topology.json')
        self.p['tasks'].insert(1,dict(id='body',kind='three_phase_ifc',depends_on='study',ifc='cable-fixture/connected-cables.ifc',binding='cable-fixture/binding.json'))
        self.p['tasks'][3]['requires_pass'].append('body')
        with self.assertRaisesRegex(ProjectError,'different IFC models or cable bindings'):three_phase_model_bindings(self.source,self.p['tasks'])
        self.p['tasks'].insert(3,dict(id='proxy',kind='manual',requires_pass=['body']))
        self.p['tasks'][4]['requires_pass']=['geometry','proxy']
        with self.assertRaisesRegex(ProjectError,'different IFC models or cable bindings'):three_phase_model_bindings(self.source,self.p['tasks'])

    @unittest.skipUnless(PYTHON,'requires isolated numerical runtime')
    def test_delivery_rejects_removed_model_binding_record(self):
        from bsa.delivery import context
        out=self.source/'run';execute(self.plan,out,three_phase_python=Path(PYTHON))
        file=out/'workflow.json';r=json.loads(file.read_text());self.assertTrue(r['three_phase_model_bindings'])
        r['three_phase_model_bindings']=[];file.write_text(json.dumps(r),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'model bindings differ'):context(self.plan,out)

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
