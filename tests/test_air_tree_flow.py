import copy
import unittest
from bsa.air_tree_flow import aggregate

class AirTreeFlowTests(unittest.TestCase):
    def setUp(self):
        self.tree=dict(root='R',sections=[dict(id='main',**{'from':'R','to':'J'}),dict(id='left',**{'from':'J','to':'A'}),dict(id='right',**{'from':'J','to':'B'})],leaf_terminals=dict(A=['a','b'],B=['c']),basis='Synthetic grouping')
        self.terminals=[dict(id=k,maximum_flow_L_s=v) for k,v in [('a',100),('b',200),('c',400)]]
    def test_branch_balance_and_changed_terminal_propagation(self):
        r=aggregate(self.tree,self.terminals)
        self.assertEqual(r['section_flow_L_s'],dict(main=700,left=300,right=400))
        self.terminals[0]['maximum_flow_L_s']=150
        r=aggregate(self.tree,self.terminals)
        self.assertEqual(r['section_flow_L_s'],dict(main=750,left=350,right=400))
        self.assertFalse(r['design_accepted'])
    def test_invalid_membership_topology_and_demand(self):
        variants=[]
        for membership in [dict(A=['a','b'],B=['b','c']),dict(A=['a'],B=['c']),dict(A=['a','b'],B=['x']),dict(A=['a','b'],B=[])]:
            t=copy.deepcopy(self.tree);t['leaf_terminals']=membership;variants.append(t)
        t=copy.deepcopy(self.tree);t['sections'].append(dict(id='cycle',**{'from':'B','to':'R'}));variants.append(t)
        t=copy.deepcopy(self.tree);t['sections']+= [dict(id='island1',**{'from':'X','to':'Y'}),dict(id='island2',**{'from':'Y','to':'X'})];variants.append(t)
        for t in variants:
            with self.subTest(tree=t),self.assertRaises(ValueError):aggregate(t,self.terminals)
        for value in (0,-1,True,float('inf')):
            self.terminals[0]['maximum_flow_L_s']=value
            with self.assertRaises(ValueError):aggregate(self.tree,self.terminals)
