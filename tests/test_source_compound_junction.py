import copy
import unittest
from bsa import source_compound_junction as tool


class SourceCompoundJunctionTests(unittest.TestCase):
    def fixture(self):
        def incident(s,role,ray,w,h):return dict(section=s,role=role,outward_unit_vector=ray,width_m=w,height_m=h)
        upper=dict(node='U',degree=3,point_m=[0.,.8,0.],connection_requirement='unequal_section_tee_required',incidents=[incident('A','incoming',[0,1,0],1.2,.8),incident('S','outgoing',[0,-1,0],1.,.7),incident('R','outgoing',[1,0,0],.4,.3)])
        lower=dict(node='L',degree=4,point_m=[0.,0.,0.],connection_requirement='multi_branch_connection_required',incidents=[incident('S','incoming',[0,1,0],1.,.7),incident('O','outgoing',[0,-1,0],.8,.7),incident('B','outgoing',[-1,0,0],.3,.3),incident('C','outgoing',[1,0,0],.35,.3)])
        def device(name,a,b):return dict(id=name,origin_m=[0.,0.,0.],ports=[dict(id='in',offset_m=a),dict(id='out',offset_m=b)])
        model=dict(devices=[device('A',[0,1.2,3],[0,.8,3]),device('S',[0,.8,3],[0,0,3]),device('O',[0,0,3],[0,-4,3]),device('R',[0,.8,3],[3,.8,3]),device('B',[0,0,3],[-3,0,3]),device('C',[0,0,3],[3,0,3])],connections=[{'from':'BEND-U.out','to':'A.in'}])
        basis=dict(project_uuid='0d51f671-9501-40ed-96ef-6e277bb5c753',elevation_m=dict(value=3),wall_thickness_m=dict(value=.001))
        policy=dict(upper_node='U',lower_node='L',shared_section='S',inlet_section='A',outlet_section='O',branch_reaches_m={'R':.9,'B':.9,'C':.9},outlet_reach_m=1.,maximum_included_trunk_angle_degrees=30,classification='assumed',source='Synthetic source-bound compound scenario')
        return dict(nodes=[upper,lower]),basis,model,policy

    def test_absorption_and_external_source_caps_are_explicit(self):
        args=self.fixture();original=copy.deepcopy(args);spec,fit=tool.compile_model(*args,.05)
        self.assertEqual(args,original);self.assertEqual(fit['absorbed_straight_sections'],['A','S']);self.assertEqual(fit['direct_inlet_source_port'],'BEND-U.out')
        self.assertEqual(spec['port_directions']['upper'],'SINK');self.assertEqual(len(fit['external_interfaces']),4)
        self.assertEqual(spec['stations'][1]['width_m'],1.);self.assertEqual(spec['stations'][2]['width_m'],1.)
        self.assertLess(max(fit['trunk_included_angles_degrees']),30);self.assertFalse(fit['design_accepted'])

    def test_no_saved_elbow_cap_or_changed_shared_section_rejects(self):
        args=self.fixture();args[2]['connections']=[]
        with self.assertRaisesRegex(ValueError,'elbow'):tool.compile_model(*args,.05)
        args=self.fixture();args[0]['nodes'][1]['incidents'][0]['width_m']+=.01
        with self.assertRaisesRegex(ValueError,'profile'):tool.compile_model(*args,.05)

    def test_no_budget_angle_or_branch_omission_can_be_hidden(self):
        args=self.fixture();args[3]['outlet_reach_m']=4.
        with self.assertRaisesRegex(ValueError,'budget'):tool.compile_model(*args,.05)
        args=self.fixture();args[3]['maximum_included_trunk_angle_degrees']=10
        with self.assertRaisesRegex(ValueError,'angle'):tool.compile_model(*args,.05)
        args=self.fixture();args[3]['branch_reaches_m'].pop('R')
        with self.assertRaisesRegex(ValueError,'Every'):tool.compile_model(*args,.05)


if __name__=='__main__':unittest.main()
