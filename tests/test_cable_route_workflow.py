from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.workflow import three_phase_rule_bindings, three_phase_model_bindings, inventory_source_bindings

ROOT=Path(__file__).resolve().parents[1]


class CableRouteWorkflowBindings(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name,value in [('a.ifc','model A'),('copy.ifc','model A'),('b.ifc','model B'),('binding.json','mapping'),('other.json','other mapping')]:
            (self.root/name).write_text(value)
        self.tasks=[dict(id='study',kind='three_phase_ifc_project',ifc='a.ifc',binding='binding.json'),
            dict(id='bend',kind='three_phase_bend_limits',depends_on='study',ifc='a.ifc',binding='binding.json'),
            dict(id='coordination',kind='three_phase_coordination',depends_on='study',ifc='a.ifc',binding='binding.json'),
            dict(id='drawing',kind='cable_route_drawing',depends_on='study',ifc='a.ifc',binding='binding.json',requires_pass=['bend','coordination'])]

    def test_same_model_and_gate_bindings(self):
        self.assertEqual(len(three_phase_rule_bindings(self.tasks)),2)
        self.assertEqual(len(three_phase_model_bindings(self.root,self.tasks)),5)
        self.tasks[-1]['ifc']='copy.ifc'
        self.assertEqual(len(three_phase_model_bindings(self.root,self.tasks)),5)

    def test_changed_model_rejected(self):
        self.tasks[-1]['ifc']='b.ifc'
        with self.assertRaisesRegex(ProjectError,'different IFC'):three_phase_model_bindings(self.root,self.tasks)

    def test_changed_binding_rejected(self):
        self.tasks[-1]['binding']='other.json'
        with self.assertRaisesRegex(ProjectError,'different IFC'):three_phase_model_bindings(self.root,self.tasks)

    def test_missing_gate_rejected(self):
        self.tasks[-1]['requires_pass']=['bend']
        with self.assertRaisesRegex(ProjectError,'bend and coordination'):three_phase_rule_bindings(self.tasks)

    def test_transitive_same_model_gates(self):
        self.tasks.insert(3,dict(id='bridge',kind='three_phase_ifc',depends_on='study',ifc='a.ifc',binding='binding.json',requires_pass=['bend','coordination']))
        self.tasks[-1]['requires_pass']=['bridge']
        links=three_phase_rule_bindings(self.tasks)
        self.assertEqual({r['check'] for r in links},{'bend','coordination','bridge'})
        self.assertTrue(three_phase_model_bindings(self.root,self.tasks))

    def test_different_study_gate_rejected(self):
        self.tasks.insert(3,dict(id='other-study',kind='three_phase_ifc_project',ifc='a.ifc',binding='binding.json'))
        self.tasks[-1]['depends_on']='other-study'
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(self.tasks)

    def test_inventory_checks_actual_route_model(self):
        self.tasks.insert(0,dict(id='inventory',kind='ifc_query',ifc='a.ifc'))
        self.tasks[-1]['requires_pass'].append('inventory')
        self.assertTrue(inventory_source_bindings(self.tasks,self.root))
        self.tasks[-1]['ifc']='b.ifc'
        with self.assertRaisesRegex(ProjectError,'different model'):inventory_source_bindings(self.tasks,self.root)
