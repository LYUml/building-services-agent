from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.workflow import three_phase_model_bindings,three_phase_rule_bindings,inventory_source_bindings

ROOT=Path(__file__).resolve().parents[1]


class CableRuleWorkflowBindings(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name,value in [('a.ifc','model A'),('b.ifc','model B'),('binding.json','mapping'),('other.json','different mapping')]:
            (self.root/name).write_text(value)
        self.tasks=[dict(id='study',kind='three_phase_ifc_project',ifc='a.ifc',binding='binding.json'),dict(id='rules',kind='three_phase_cable_regulations',depends_on='study',ifc='a.ifc',binding='binding.json'),dict(id='drawing',kind='three_phase_drawing',depends_on='study',requires_pass=['rules'])]

    def test_native_rule_and_drawing_bindings_registered(self):
        self.assertEqual(len(three_phase_rule_bindings(self.tasks)),1)
        self.assertEqual(len(three_phase_model_bindings(self.root,self.tasks)),2)

    def test_other_model_or_binding_rejected(self):
        for field,value in [('ifc','b.ifc'),('binding','other.json')]:
            old=self.tasks[1][field];self.tasks[1][field]=value
            with self.assertRaisesRegex(ProjectError,'different IFC'):three_phase_model_bindings(self.root,self.tasks)
            self.tasks[1][field]=old

    def test_other_study_gate_rejected(self):
        self.tasks.insert(2,dict(id='other',kind='three_phase'))
        self.tasks[-1]['depends_on']='other'
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(self.tasks)

    def test_inventory_uses_explicit_rule_model(self):
        self.tasks.insert(0,dict(id='inventory',kind='ifc_query',ifc='a.ifc'))
        self.tasks[2]['requires_pass']=['inventory']
        self.assertTrue(inventory_source_bindings(self.tasks,self.root))
        self.tasks[2]['ifc']='b.ifc'
        with self.assertRaisesRegex(ProjectError,'different model'):inventory_source_bindings(self.tasks,self.root)
