import json
from pathlib import Path
import runpy
import tempfile
import unittest
import ifcopenshell
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase_topology import inspect,run

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/three-phase-network/project.json'


class SavedElectricalGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(PROJECT,PROJECT.parent/'cable-geometry.json',cls.root/'cables','extrusion')
        connect=runpy.run_path(str(ROOT/'scripts/author_three_phase_topology_fixture.py'))['run']
        connect(PROJECT,cls.root/'cables/cables.ifc',cls.root/'cables/binding.json',PROJECT.parent/'topology-geometry.json',cls.root/'connected')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        import shutil
        self.folder=self.root/self._testMethodName
        shutil.copytree(self.root/'connected',self.folder)
        self.ifc=self.folder/'connected-cables.ifc';self.binding=self.folder/'binding.json';self.topology=self.folder/'topology-binding.json'

    def check(self):return inspect(PROJECT,self.ifc,self.binding,self.topology)

    def mutate(self,change):
        m=ifcopenshell.open(str(self.ifc));t=json.loads(self.topology.read_text());change(m,t);m.write(str(self.ifc))
        b=json.loads(self.binding.read_text());b['ifc_sha256']=digest(self.ifc);t['ifc_sha256']=digest(self.ifc)
        self.binding.write_text(json.dumps(b),encoding='utf-8');self.topology.write_text(json.dumps(t),encoding='utf-8')

    def test_actual_native_graph_and_scope(self):
        before=digest(self.ifc);r=run(PROJECT,self.ifc,self.binding,self.topology,self.folder/'check')
        self.assertTrue(r['native_port_relationships_pass']);self.assertTrue(r['logical_graph_correspondence_pass'])
        self.assertEqual((r['bus_count'],r['cable_count'],r['directed_relationship_count']),(3,2,8))
        self.assertFalse(r['physical_installation_verified']);self.assertFalse(r['design_accepted'])
        self.assertEqual(digest(self.ifc),before)

    def test_missing_directed_half_rejected(self):
        self.mutate(lambda m,t:m.remove(m.by_type('IfcRelConnectsPorts')[0]))
        with self.assertRaisesRegex(ProjectError,'relationships differ'):self.check()

    def test_duplicate_relationship_rejected(self):
        def edit(m,t):
            r=m.by_type('IfcRelConnectsPorts')[0]
            m.create_entity('IfcRelConnectsPorts',GlobalId=ifcopenshell.guid.new(),RelatingPort=r.RelatingPort,RelatedPort=r.RelatedPort)
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'relationships differ'):self.check()

    def test_wrong_board_connection_rejected(self):
        def edit(m,t):
            r=m.by_type('IfcRelConnectsPorts')[0]
            other=t['buses']['load-B']['ports']['branch']
            r.RelatedPort=m.by_guid(other)
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'relationships differ'):self.check()

    def test_same_anchor_swapped_declared_board_ports_rejected(self):
        t=json.loads(self.topology.read_text());ports=t['buses']['DB-A']['ports']
        ports['feeder'],ports['branch']=ports['branch'],ports['feeder']
        self.topology.write_text(json.dumps(t),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'relationships differ'):self.check()

    def test_unowned_board_port_rejected(self):
        def edit(m,t):
            board=m.by_guid(t['buses']['DB-A']['element_guid'])
            relation=next(r for r in board.IsNestedBy if r.is_a('IfcRelNests'))
            relation.RelatedObjects=relation.RelatedObjects[:1]
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'ownership/count'):self.check()

    def test_moved_board_ports_rejected(self):
        def edit(m,t):
            board=m.by_guid(t['buses']['DB-A']['element_guid'])
            location=board.ObjectPlacement.RelativePlacement.Location
            point=list(location.Coordinates);point[0]+=.1;location.Coordinates=point
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'bus anchor'):self.check()

    def test_non_electrical_board_port_rejected(self):
        self.mutate(lambda m,t:setattr(m.by_guid(t['buses']['source']['ports']['feeder']),'SystemType','VENTILATION'))
        with self.assertRaisesRegex(ProjectError,'electrical cable port'):self.check()

    def test_missing_common_node_basis_rejected(self):
        t=json.loads(self.topology.read_text());t['internal_bus_model']='unspecified'
        self.topology.write_text(json.dumps(t),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'ideal common'):self.check()

    def test_extra_nesting_owner_rejected(self):
        def edit(m,t):
            port=m.by_guid(t['buses']['DB-A']['ports']['feeder'])
            other=m.create_entity('IfcBuildingElementProxy',GlobalId=ifcopenshell.guid.new(),Name='Unmapped extra owner')
            m.create_entity('IfcRelNests',GlobalId=ifcopenshell.guid.new(),RelatingObject=other,RelatedObjects=[port])
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'exactly one declared nesting owner'):self.check()

    def test_changed_basis_rejected(self):
        with (self.folder/'topology-source.json').open('a') as f:f.write(' ')
        with self.assertRaisesRegex(ProjectError,'source path/hash'):self.check()
