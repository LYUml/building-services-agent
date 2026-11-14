import copy
import math
import unittest
import ezdxf
from bsa.vav_recenter import revised,compensate
from bsa.duct_sheet import snapshot


def fixture():
    doc=ezdxf.new();doc.units=6;m=doc.modelspace()
    layers=dict(supply='duct',vav='vav',terminal='terminal',flex='flex')
    tree=dict(root='R',sections=[],leaf_terminals={},basis='Explicit synthetic topology')
    binding=dict(sections={});allocation=dict(terminals=[])
    nodes=dict(R=[0,5,0],T1=[2,5,0],T2=[8,5,0],VA=[2,2,0],VB=[8,2,0])
    for sid,a,b in [('S1','R','T1'),('S2','T1','T2'),('A','T1','VA'),('B','T2','VB')]:
        line=m.add_line(nodes[a],nodes[b],dxfattribs=dict(layer='duct'))
        m.add_text(sid,dxfattribs=dict(layer='label',height=.1,insert=((nodes[a][0]+nodes[b][0])/2,(nodes[a][1]+nodes[b][1])/2,0)))
        tree['sections'].append(dict(id=sid,**{'from':a,'to':b}))
        binding['sections'][sid]=dict(line_handle=line.dxf.handle,from_node=a,to_node=b,from_m=nodes[a],to_m=nodes[b])
    for name,cx in [('VA',3),('VB',8)]:
        m.add_circle(nodes[name],.1,dxfattribs=dict(layer='vav'))
        m.add_text(name,dxfattribs=dict(layer='label',height=.1,insert=nodes[name]))
        tree['leaf_terminals'][name]=[]
        for index,(x,y) in enumerate([(cx-1,1),(cx+1,1),(cx+1,3),(cx-1,3)]):
            tid=name+str(index);tree['leaf_terminals'][name].append(tid)
            allocation['terminals'].append(dict(id=tid,center_m=[x,y],maximum_flow_L_s=100,minimum_flow_L_s=40))
            m.add_lwpolyline([(x-.1,y-.1),(x+.1,y-.1),(x+.1,y+.1),(x-.1,y+.1)],close=True,dxfattribs=dict(layer='terminal'))
            m.add_line(nodes[name],(x,y,0),dxfattribs=dict(layer='flex'))
    obstacle=m.add_lwpolyline([(20,20),(21,20),(21,21),(20,21)],close=True)
    obstacles=[dict(id='column',polygon_m=[[20,20],[21,20],[21,21],[20,21]],source_handles=[obstacle.dxf.handle],source='Explicit synthetic distant column')]
    schedule=dict(status='pass',sections=[dict(id=sid,inputs=dict(width_m=.2),calculation=dict(checked=True),failures=[]) for sid in binding['sections']])
    return doc,allocation,tree,binding,layers,schedule,obstacles


class VAVRecenterTests(unittest.TestCase):
    def test_relocates_tap_without_added_bend_or_flow_change(self):
        args=fixture();before=snapshot(args[0]);a=copy.deepcopy(args[1]);t=copy.deepcopy(args[2])
        binding,result=revised(*args)
        self.assertEqual(binding['sections']['A']['to_m'],[3,2,0])
        self.assertEqual(binding['sections']['A']['from_m'],[3,5,0])
        self.assertEqual(binding['sections']['S1']['to_m'],[3,5,0])
        self.assertEqual(binding['sections']['S2']['from_m'],[3,5,0])
        self.assertAlmostEqual(result['revised_max_flex_plan_m'],math.sqrt(2))
        self.assertLess(result['revised_total_flex_plan_m'],result['baseline_total_flex_plan_m'])
        self.assertAlmostEqual(result['revised_total_rigid_centreline_m'],result['baseline_total_rigid_centreline_m'])
        self.assertEqual(args[1],a);self.assertEqual(args[2],t)
        self.assertEqual(result['added_bends'],0)
        self.assertEqual(set(before),set(snapshot(args[0])))
        self.assertFalse(result['design_accepted'])

    def test_repeated_source_geometry_needs_no_further_revision(self):
        args=list(fixture());binding,_=revised(*args);args[3]=binding
        with self.assertRaisesRegex(ValueError,'No strict'):revised(*args)

    def test_nonrectangular_group_rejected(self):
        args=list(fixture());args[1]['terminals'][0]['center_m']=[2.1,1]
        # Update matching saved symbol and line to isolate rectangular-family rejection.
        doc=args[0];symbol=next(e for e in doc.modelspace() if e.dxf.layer=='terminal')
        symbol.translate(.1,0,0)
        line=next(e for e in doc.modelspace() if e.dxf.layer=='flex');line.dxf.end=(2.1,1,0)
        with self.assertRaisesRegex(ValueError,'four-corner'):revised(*args)

    def test_reversed_trunk_rejected(self):
        args=list(fixture())
        # Moving T1 from x=2 to x=3 would reverse its incoming section.
        doc=args[0];entry=args[3]['sections']['S1'];entry['from_m']=[2.5,5,0]
        doc.entitydb[entry['line_handle']].dxf.start=(2.5,5,0)
        with self.assertRaisesRegex(ValueError,'reversal'):revised(*args)

    def test_nominal_width_column_collision_rejected(self):
        args=list(fixture());doc=args[0]
        polygon=[[2.95,3.8],[3.05,3.8],[3.05,4.2],[2.95,4.2]]
        outline=doc.modelspace().add_lwpolyline(polygon,close=True)
        args[-1]=[dict(id='blocked',polygon_m=polygon,source_handles=[outline.dxf.handle],source='Synthetic fixed column')]
        with self.assertRaisesRegex(ValueError,'overlaps'):revised(*args)

    def test_changed_obstacle_source_and_extra_flex_rejected(self):
        args=list(fixture());args[-1][0]['polygon_m'][0][0]=19.9
        with self.assertRaisesRegex(ValueError,'outlines'):revised(*args)
        args=list(fixture());args[0].modelspace().add_line((0,0),(1,1),dxfattribs=dict(layer='flex'))
        with self.assertRaisesRegex(ValueError,'Unbound'):revised(*args)

    def test_terminal_end_tap_can_slide_with_rigid_total_not_increased(self):
        args=list(fixture());doc=args[0]
        for t in args[1]['terminals'][4:]: t['center_m']=[t['center_m'][0]+1,t['center_m'][1]+1.2]
        for e in list(doc.modelspace()):
            if e.dxf.layer=='terminal' and min(p[0] for p in e.get_points())>6:e.translate(1,1.2,0)
            if e.dxf.layer=='flex' and e.dxf.end.x>6:e.dxf.end=(e.dxf.end.x+1,e.dxf.end.y+1.2,0)
        binding,result=revised(*args)
        self.assertEqual(binding['sections']['B']['from_m'],[9,5,0])
        self.assertEqual(binding['sections']['B']['to_m'][0],9)
        self.assertAlmostEqual(binding['sections']['B']['to_m'][1],3.2,places=12)
        self.assertEqual(binding['sections']['B']['to_m'][2],0)
        self.assertLessEqual(result['revised_total_rigid_centreline_m'],result['baseline_total_rigid_centreline_m'])

    def test_schedule_cell_with_same_section_text_stays_fixed(self):
        args=list(fixture());doc=args[0]
        text=doc.modelspace().add_text('A',dxfattribs=dict(layer='schedule',height=.1,insert=(30,30,0)))
        args[3]['sections']['A']['cells']=[dict(handle=text.dxf.handle,expected_text='A')]
        revised(*args)
        self.assertEqual(tuple(text.dxf.insert),(30,30,0))

    def test_friction_compensation_preserves_source_caps_grid_and_input(self):
        args=list(fixture());old=copy.deepcopy(args[3]);binding,_=revised(*args)
        schedule=copy.deepcopy(args[5])
        for row in schedule['sections']:row['calculation']['friction_Pa_m']=1.
        project=dict(basis='Original source',sections=[dict(id=name,limits=dict(friction_Pa_m=1.23,actual_velocity_m_s=8,aspect_ratio=4),candidates=[dict(id='original',width_m=.2,height_m=.2)]) for name in old['sections']])
        preserved=copy.deepcopy(project)
        result,caps=compensate(project,schedule,old,binding)
        self.assertEqual(project,preserved)
        self.assertEqual([c['section'] for c in caps],['S1'])
        self.assertAlmostEqual(caps[0]['derived_limit_Pa_m'],2/3,places=12)
        for original,new in zip(project['sections'],result['sections']):
            self.assertEqual(original['candidates'],new['candidates'])
            self.assertEqual(original['limits']['actual_velocity_m_s'],new['limits']['actual_velocity_m_s'])
            self.assertEqual(original['limits']['aspect_ratio'],new['limits']['aspect_ratio'])
            self.assertLessEqual(new['limits']['friction_Pa_m'],original['limits']['friction_Pa_m'])

    def test_length_compensation_without_inherited_grid_rejects(self):
        args=list(fixture());old=copy.deepcopy(args[3]);binding,_=revised(*args)
        schedule=copy.deepcopy(args[5])
        for row in schedule['sections']:row['calculation']['friction_Pa_m']=1.
        project=dict(basis='Original source',sections=[dict(id=name,limits=dict(friction_Pa_m=1.23)) for name in old['sections']])
        with self.assertRaisesRegex(ValueError,'finite size'):compensate(project,schedule,old,binding)


if __name__=='__main__':unittest.main()
