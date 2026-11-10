import unittest
import ezdxf
from bsa.air_terminal_drawing import inspect


class TerminalDrawingTests(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new();self.doc.units=6
        self.layers=dict(supply='duct',vav='vav',terminal='terminal',flex='flex')
        self.tree=dict(root='R',sections=[dict(id='A',**{'from':'R','to':'VA'}),dict(id='B',**{'from':'R','to':'VB'})],leaf_terminals=dict(VA=['TA'],VB=['TB']),basis='Synthetic test')
        self.allocation=dict(terminals=[dict(id='TA',center_m=[2,1],maximum_flow_L_s=100),dict(id='TB',center_m=[2,-1],maximum_flow_L_s=100)])
        self.binding=dict(sections={})
        m=self.doc.modelspace()
        for sid,node,y in [('A','VA',1),('B','VB',-1)]:
            m.add_line((0,0),(1,y),dxfattribs=dict(layer='duct'))
            m.add_circle((1,y),.1,dxfattribs=dict(layer='vav'))
            m.add_line((1,y),(2,y),dxfattribs=dict(layer='flex'))
            m.add_lwpolyline([(1.9,y-.1),(2.1,y-.1),(2.1,y+.1),(1.9,y+.1)],close=True,dxfattribs=dict(layer='terminal'))
            self.binding['sections'][sid]=dict(from_node='R',to_node=node,from_m=[0,0,0],to_m=[1,y,0])

    def check(self):
        return inspect(self.doc,self.allocation,self.tree,self.binding,self.layers)

    def test_actual_geometry_and_reversed_lines(self):
        for e in self.doc.modelspace().query('LINE'):
            e.dxf.start,e.dxf.end=e.dxf.end,e.dxf.start
        r=self.check()
        self.assertEqual(r['terminal_count'],2)
        self.assertAlmostEqual(r['maximum_plan_length_m'],1)
        self.assertFalse(r['design_accepted'])

    def test_same_counts_and_flows_wrong_membership(self):
        self.tree['leaf_terminals']=dict(VA=['TB'],VB=['TA'])
        with self.assertRaisesRegex(ValueError,'correspondence'):self.check()

    def test_disconnected_flex(self):
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='flex')
        e.dxf.start=(1.01,1,0)
        with self.assertRaisesRegex(ValueError,'correspondence'):self.check()

    def test_extra_geometry_and_nonplanar_symbol(self):
        e=self.doc.modelspace().add_line((9,9),(10,10),dxfattribs=dict(layer='flex'))
        with self.assertRaisesRegex(ValueError,'Unbound'):self.check()
        self.doc.modelspace().delete_entity(e)
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='terminal')
        e.dxf.elevation=.1
        with self.assertRaisesRegex(ValueError,'planar'):self.check()

    def test_shifted_group_and_duplicate_symbol(self):
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='vav')
        before=e.dxf.center;e.dxf.center=(1.1,1,0)
        with self.assertRaisesRegex(ValueError,'correspondence'):self.check()
        e.dxf.center=before
        e=next(e for e in self.doc.modelspace() if e.dxf.layer=='terminal')
        self.doc.modelspace().add_entity(e.copy())
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.check()
