import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
from bsa.cli import digest
from bsa.coordination_recovery import recover
from bsa.workflow_status import diagnose
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]

class CoordinationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);(self.root/'coordination').mkdir();(self.root/'producer').mkdir()
        model=ifcopenshell.file(schema='IFC4');api.run('root.create_entity',model,ifc_class='IfcProject');length=api.run('unit.add_si_unit',model,unit_type='LENGTHUNIT');api.run('unit.assign_unit',model,units=[length])
        self.a=api.run('root.create_entity',model,ifc_class='IfcDuctSegment',name='Synthetic Stub');self.b=api.run('root.create_entity',model,ifc_class='IfcAirTerminal',name='Synthetic Terminal')
        for obj in (self.a,self.b):api.run('geometry.edit_object_placement',model,product=obj,matrix=np.eye(4),is_si=True)
        source=api.run('system.add_port',model,element=self.a);source.FlowDirection='SOURCE';sink=api.run('system.add_port',model,element=self.b);sink.FlowDirection='SINK'
        for port in (source,sink):api.run('geometry.edit_object_placement',model,product=port,matrix=np.eye(4),is_si=True)
        api.run('system.connect_port',model,port1=source,port2=sink,direction='SOURCE');pset=api.run('pset.add_pset',model,product=self.b,name='BSA_SpatialTerminal');api.run('pset.edit_pset',model,pset=pset,properties=dict(InputID='T1'))
        self.ifc=self.root/'producer/Terminal Stub Study.ifc';model.write(str(self.ifc));producer=self.root/'producer/terminal-stubs.json';producer.write_text('{}')
        policy=self.root/'policy.json';policy.write_text(json.dumps(dict(minimum_clearance_m=.05,source='Synthetic policy control,not regulation')))
        finding=dict(pair=[self.a.GlobalId,self.b.GlobalId],type='controlled_clearance',engine_distance_m=0)
        calculation=dict(elements=[dict(guid=o.GlobalId,name=o.Name,ifc_class=o.is_a()) for o in (self.a,self.b)],intersections=[],clearance_violations=[finding],missing_geometry_guids=[],invalid_geometry=[],unrepresented_elements=[],unverified_solid_pairs=[])
        self.record=dict(terminal_ifc=str(producer),policy=str(policy),inputs={str(p):digest(p) for p in (producer,self.ifc,policy)},summary=dict(status='fail',added_terminal_guids=[self.b.GlobalId]),calculation=calculation)
        self.path=self.root/'coordination/terminal-coordination.json';self.path.write_text(json.dumps(self.record));self.report=dict(artifact_hashes={'coordination/terminal-coordination.json':digest(self.path)},tasks={'model':dict(kind='spatial_terminal_stubs',status='pass',scope='Synthetic control'),'coordination':dict(kind='spatial_terminal_coordination',status='fail',scope='Synthetic policy failure'),'review':dict(kind='manual',status='pending',scope='Dependent review')})
        self.plan=self.root/'plan.json';self.source=dict(tasks=[dict(id='model',kind='spatial_terminal_stubs'),dict(id='coordination',kind='spatial_terminal_coordination',depends_on='model'),dict(id='review',kind='manual',requires_pass=['coordination'])],requirements=[dict(id='R1',task='model'),dict(id='R2',task='coordination'),dict(id='R3',task='review')]);self.plan.write_text(json.dumps(self.source));(self.root/'workflow.json').write_text(json.dumps(self.report))

    def test_native_link_requests_and_dependency_requirements_preserved(self):
        requests=recover(self.root,self.report,'coordination');row=requests['data_requests'][0]
        self.assertEqual(row['code'],'connected_interface_geometry_policy_review');self.assertEqual(row['logical_downstream_terminal_ids'],['T1']);self.assertEqual(row['minimum_clearance_m'],.05);self.assertEqual(len(row['recorded_direct_port_links']),1);self.assertEqual(row['status'],'open');self.assertFalse(requests['design_accepted'])
        with patch('bsa.workflow_status.context',return_value=(self.source,self.report,dict(integrity_pass=True))):result=diagnose(self.plan,self.root)
        action=next(r for r in result['actions'] if r['task']=='coordination');self.assertEqual(action['affected_tasks'],['coordination','review']);self.assertEqual([r['id'] for r in action['affected_requirements']],['R2','R3']);self.assertIn('do not waive',action['next_action']);self.assertFalse(result['execution_pass'])

    def test_changed_model_rejected_and_pending_task_has_no_fabricated_requests(self):
        self.ifc.write_bytes(self.ifc.read_bytes()+b'changed')
        with self.assertRaisesRegex(ProjectError,'source/method changed'):recover(self.root,self.report,'coordination')
        self.assertEqual(recover(self.root,dict(artifact_hashes={}), 'not-executed'),{})
