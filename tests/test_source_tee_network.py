import copy
import unittest
import numpy as np
from unittest.mock import patch
from bsa import source_tee_network as tool


class SourceTeeNetworkTests(unittest.TestCase):
    def fixture(self):
        d=dict(id='S',ifc_class='IfcDuctSegment',origin_m=[0.,-.301,-.151],size_m=[3.,.602,.302],
            body_shape='straight rectangular duct wall',properties=dict(InternalWidth_m=.6,InternalHeight_m=.3,WallThickness_m=.001),
            ports=[dict(id='in',offset_m=[0.,.301,.151],direction='SINK'),dict(id='out',offset_m=[3.,.301,.151],direction='SOURCE')])
        model=dict(devices=[d]); junction=dict(nodes=[dict(node='A',incidents=[dict(section='S',role='outgoing')]),dict(node='B',incidents=[dict(section='S',role='incoming')])])
        rows={name:dict(fit=dict(arms=[dict(section='S',arm='branch',width_m=.6,height_m=.3,outward_reach_m=reach)])) for name,reach in [('A',.4),('B',.7)]}
        selected=dict(policy=dict(minimum_remainder_m=dict(value=.05)))
        return model,junction,selected,rows

    def test_both_end_native_straight_trim_retains_sources(self):
        args=self.fixture(); original=copy.deepcopy(args)
        with patch.object(tool.bim,'validate'):
            model,links,budgets=tool.compile_model(*args,{})
        self.assertEqual(args,original)
        self.assertAlmostEqual(model['devices'][0]['origin_m'][0],.4)
        self.assertAlmostEqual(model['devices'][0]['size_m'][0],1.9)
        self.assertEqual({(r['node'],r['port']) for r in links},{('A','in'),('B','out')})
        self.assertAlmostEqual(budgets[0]['remaining_m'],1.9)
        self.assertFalse(model['devices'][0]['properties']['AllFittingTrimsKnown'])

    def test_blocked_node_is_not_trimmed_or_connected(self):
        with patch.object(tool.bim,'validate'):
            model,links,budgets=tool.compile_model(*self.fixture(),{'A':['Retained original failure']})
        self.assertEqual(model['devices'][0]['origin_m'][0],0)
        self.assertAlmostEqual(budgets[0]['remaining_m'],2.3)
        self.assertEqual([r['node'] for r in links],['B'])

    def test_both_end_overrun_rejects_before_authoring(self):
        args=self.fixture(); args[3]['B']['fit']['arms'][0]['outward_reach_m']=2.6
        with self.assertRaisesRegex(ValueError,'budget'):
            tool.compile_model(*args,{})

    def test_saved_cap_and_section_roll_are_required(self):
        from bsa.tee_geometry import stable_guid
        spec=dict(project_uuid='e307360f-2365-4f9a-8f78-d96dfba5fddb')
        owner=stable_guid(spec,'IfcDuctFitting','RECTANGULAR-TEE')
        first=np.eye(4); last=np.diag([1.,-1.,-1.,1.])
        expected=dict(objects={'segment':dict(name='S',ifc_class='IfcDuctSegment',frame=first.tolist()),owner:dict(name='T',ifc_class='IfcDuctFitting',frame=first.tolist())},
            ports={'s':dict(owner='segment',name='out',direction='SOURCE',frame=first.tolist()),'t':dict(owner=owner,name='main-a',direction='SINK',frame=last.tolist())})
        interfaces=[dict(node='J',arm='main-a',section='S',port='out')]
        rows={'J':dict(spec=spec,children={})}
        self.assertEqual(tool.external_links(expected,interfaces,rows),[('s','t')])
        wrong=copy.deepcopy(expected); wrong['ports']['t']['frame'][0][3]=.01
        with self.assertRaisesRegex(ValueError,'cap'):tool.external_links(wrong,interfaces,rows)
        wrong=copy.deepcopy(expected); wrong['ports']['t']['frame']=np.array([[0,1,0,0],[1,0,0,0],[0,0,-1,0],[0,0,0,1.]]).tolist()
        with self.assertRaisesRegex(ValueError,'roll'):tool.external_links(wrong,interfaces,rows)


if __name__=='__main__': unittest.main()
