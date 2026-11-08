import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
from bsa.engine import ProjectError
from bsa.route_annotations import layout, path, crosses

ROOT = Path(__file__).resolve().parents[1]


def source_rows(example, axes):
    model = json.loads((ROOT/'examples'/example/'project.json').read_text())
    rows = []
    for d in model['devices']:
        row = dict(guid=d['id'], outside_diameter_m=d['properties']['OutsideDiameter_m'],
                   start_world_m=[a+b for a,b in zip(d['origin_m'],d['ports'][0]['offset_m'])],
                   end_world_m=[a+b for a,b in zip(d['origin_m'],d['ports'][1]['offset_m'])], centreline_radius_m=None)
        if 'CenterlineRadius_m' in d['properties']:
            c = [d['arc_center_m'][i] for i in axes]
            angles = [math.degrees(math.atan2(p[axes[1]]-c[1],p[axes[0]]-c[0]))%360 for p in (row['start_world_m'],row['end_world_m'])]
            if not math.isclose((angles[1]-angles[0])%360,90): angles.reverse()
            row.update(centreline_radius_m=d['properties']['CenterlineRadius_m'],projected_centre_m=c,start_angle_deg=angles[0],end_angle_deg=angles[1])
        rows.append(row)
    return rows


def occupied(p, row, axes):
    """Independent sample check against actual OD strips/annular sectors, not leader boxes."""
    a,b = [[v[i] for i in axes] for v in (row['start_world_m'],row['end_world_m'])]
    ro = row['outside_diameter_m']/2
    if row['centreline_radius_m'] is None:
        dx,dy = b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        along=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length
        away=abs((p[0]-a[0])*dy-(p[1]-a[1])*dx)/length
        return 1e-8 < along < length-1e-8 and away < ro-1e-8
    c=row['projected_centre_m'];r=math.dist(p,c);theta=math.degrees(math.atan2(p[1]-c[1],p[0]-c[0]))%360
    return (theta-row['start_angle_deg'])%360 < 90-1e-8 and row['centreline_radius_m']-ro+1e-8 < r < row['centreline_radius_m']+ro-1e-8


class RouteAnnotationTests(unittest.TestCase):
    def test_u_route_with_column_uses_external_label_rows_without_crossing(self):
        from bsa.route_optimize import select
        root=ROOT/'examples/route-search'
        _,selection=select(*(json.loads((root/name).read_text()) for name in ('route-input.json','model-settings.json','network.json')))
        rows=[]
        for index,piece in enumerate(selection['selected_route']['pieces']):
            row=dict(guid=str(index),outside_diameter_m=.1,start_world_m=piece['start_m']+[1],end_world_m=piece['end_m']+[1],centreline_radius_m=None)
            if piece['kind']=='elbow':
                c=piece['centre_m'];angles=[math.degrees(math.atan2(p[1]-c[1],p[0]-c[0]))%360 for p in (piece['start_m'],piece['end_m'])]
                if not math.isclose((angles[1]-angles[0])%360,90):angles.reverse()
                row.update(centreline_radius_m=.2,projected_centre_m=c,start_angle_deg=angles[0],end_angle_deg=angles[1])
            rows.append(row)
        box=[1.8,1,2.2,2];result=layout(rows,[0,1],.08,[box])
        self.assertGreater(result['candidate_assignments_tested'],120)
        for item in result['pieces']:
            self.assertGreater(item['label_position_m'][1],2)
            self.assertTrue(all(p[0] <= item['label_position_m'][0]-.08+1e-8
                                for p in item['leader_points_m']))
            for a,b in zip(item['leader_points_m'],item['leader_points_m'][1:]):
                self.assertFalse(crosses(a,b,box))
                for t in range(1,100):
                    p=[a[i]+t/100*(b[i]-a[i]) for i in (0,1)]
                    self.assertFalse(any(occupied(p,r,[0,1]) for r in rows))

    def test_external_obstacle_blocks_outward_stub(self):
        from bsa.route_annotations import geometry
        rows=source_rows('circular-elbow',[0,1])
        p=geometry(rows[0],[0,1],.06)['anchor_m']
        box=[p[0]-.01,p[1]-.01,p[0]+.01,p[1]+.01]
        with self.assertRaisesRegex(ProjectError,'layout not proven'):
            layout(rows,[0,1],.06,[box])

    def test_both_independent_projects_have_no_leader_samples_inside_any_pipe(self):
        for example,axes in [('circular-elbow',[0,1]),('elbow-riser',[0,2])]:
            rows=source_rows(example,axes);result=layout(rows,axes,.06)
            for item in result['pieces']:
                for a,b in zip(item['leader_points_m'],item['leader_points_m'][1:]):
                    for t in range(1,100):
                        p=[a[i]+t/100*(b[i]-a[i]) for i in (0,1)]
                        self.assertFalse(any(occupied(p,r,axes) for r in rows),(example,item['guid'],p))
            positions=sorted(p['label_position_m'][1] for p in result['pieces'])
            self.assertTrue(all(b-a >= .132-1e-10 for a,b in zip(positions,positions[1:])))
            def intersect(a,b,c,d):
                if any(max(min(a[i],b[i]),min(c[i],d[i])) > min(max(a[i],b[i]),max(c[i],d[i]))+1e-10 for i in (0,1)): return False
                def turn(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
                return turn(a,b,c)*turn(a,b,d)<=1e-12 and turn(c,d,a)*turn(c,d,b)<=1e-12
            for i,first in enumerate(result['pieces']):
                for second in result['pieces'][i+1:]:
                    self.assertFalse(any(intersect(a,b,c,d) for a,b in zip(first['leader_points_m'],first['leader_points_m'][1:])
                                         for c,d in zip(second['leader_points_m'],second['leader_points_m'][1:])))
            if example=='elbow-riser':
                by_id={p['guid']:p for p in result['pieces']}
                self.assertGreater(by_id['TURN']['label_position_m'][1],by_id['BRANCH']['label_position_m'][1])
                self.assertGreater(result['candidate_assignments_tested'],1)

    def test_historical_negative_quadrant_leader_really_crossed_branch(self):
        rows=source_rows('elbow-riser',[0,2]);branch=next(r for r in rows if r['guid']=='BRANCH')
        self.assertTrue(occupied([4.5,2.7386],branch,[0,2]))

    def test_blocked_escape_fails_instead_of_drawing_through_obstacles(self):
        rows=[dict(guid=name,start_world_m=[0,y,0],end_world_m=[1,y,0],outside_diameter_m=.1,centreline_radius_m=None) for name,y in [('A',0),('B',.08)]]
        with self.assertRaisesRegex(ProjectError,'not proven'): layout(rows,[0,1],.06)

    def test_visibility_grid_detours_and_budget_is_enforced(self):
        box=[-1,-1,1,1];result=path([-2,0],[2,0],[box],.06)
        self.assertIsNotNone(result)
        self.assertTrue(any(abs(p[1])>=1 for p in result))
        self.assertTrue(all(not crosses(a,b,box) for a,b in zip(result,result[1:])))
        with patch('bsa.route_annotations.MAX_NODES',1),self.assertRaisesRegex(ProjectError,'budget'):
            path([-2,0],[2,0],[box],.06)

    def test_outward_stubs_in_all_four_arc_quadrants(self):
        for start in (0,90,180,270):
            row=dict(guid='ARC',centreline_radius_m=.24,outside_diameter_m=.075,projected_centre_m=[0,0],start_angle_deg=start,end_angle_deg=(start+90)%360,
                     start_world_m=[.24*math.cos(math.radians(start)),.24*math.sin(math.radians(start)),0],
                     end_world_m=[.24*math.cos(math.radians(start+90)),.24*math.sin(math.radians(start+90)),0])
            result=layout([row],[0,1],.06)
            for a,b in zip(result['pieces'][0]['leader_points_m'],result['pieces'][0]['leader_points_m'][1:]):
                for t in range(1,100):
                    p=[a[i]+t/100*(b[i]-a[i]) for i in (0,1)]
                    self.assertFalse(occupied(p,row,[0,1]))


if __name__=='__main__':unittest.main()
