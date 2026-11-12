import copy
import math
import unittest

from bsa.engine import ProjectError
from bsa.route_search import search


def fixture():
    return dict(source='Synthetic routing test; dimensions are declared assumptions',units='m',
                grid_origin_m=[0,0],grid_counts=[9,7],grid_step_m=.5,
                start_m=[0,1.5],end_m=[4,1.5],outside_diameter_m=.1,
                bend_radius_m=.2,clearance_m=.1,obstacles=[])


class RouteSearchTests(unittest.TestCase):
    def test_unobstructed_route_preserves_endpoints_and_true_length(self):
        result=search(fixture())
        self.assertEqual(result['vertices_m'],[[0,1.5],[4,1.5]])
        self.assertEqual(result['length_m'],4)
        self.assertEqual(result['bend_count'],0)
        self.assertFalse(result['design_accepted'])

    def test_detour_uses_finite_bends_and_independent_length_formula(self):
        data=fixture()
        data['obstacles']=[dict(id='column',min_m=[1.8,1],max_m=[2.2,2],source='Synthetic column envelope')]
        result=search(data)
        self.assertTrue(result['route_found'])
        vertices=result['vertices_m']
        sharp=sum(math.dist(a,b) for a,b in zip(vertices,vertices[1:]))
        expected=sharp-result['bend_count']*.4+result['bend_count']*math.pi*.1
        self.assertAlmostEqual(result['length_m'],expected)
        self.assertGreater(result['length_m'],4)
        for a,b in zip(result['pieces'],result['pieces'][1:]):
            self.assertEqual(a['end_m'],b['start_m'])
        # Independently sample each actual arc/straight against the rectangular
        # obstacle. OD+clearance is checked, not only the polyline vertices.
        for piece in result['pieces']:
            for i in range(101):
                t=i/100
                if piece['kind']=='straight':
                    p=[a+(b-a)*t for a,b in zip(piece['start_m'],piece['end_m'])]
                else:
                    c=piece['centre_m'];u=[piece['start_m'][k]-c[k] for k in (0,1)];v=[piece['end_m'][k]-c[k] for k in (0,1)]
                    p=[c[k]+u[k]*math.cos(t*math.pi/2)+v[k]*math.sin(t*math.pi/2) for k in (0,1)]
                gap=math.hypot(max(1.8-p[0],0,p[0]-2.2),max(1-p[1],0,p[1]-2))
                self.assertGreaterEqual(gap,.15-1e-9)

    def test_blocked_grid_retains_failure_instead_of_fabricating_route(self):
        data=fixture();data['obstacles']=[dict(id='wall',min_m=[1.8,-1],max_m=[2.2,4],source='Synthetic full barrier')]
        result=search(data)
        self.assertFalse(result['route_found'])
        self.assertNotIn('pieces',result)

    def test_bad_inputs_and_infeasible_bend_spacing_are_rejected(self):
        for key,value in [('bend_radius_m',.25),('outside_diameter_m',.4),('grid_counts',[1000,1000]),('start_m',[.01,1.5]),('clearance_m',-1),('units','mm'),('source','')]:
            data=fixture();data[key]=value
            with self.subTest(key=key),self.assertRaises(ProjectError):search(data)

    def test_end_inside_clearance_zone_is_rejected(self):
        data=fixture();data['obstacles']=[dict(id='wall',min_m=[-.1,1.6],max_m=[.1,1.8],source='Synthetic obstacle near start')]
        with self.assertRaisesRegex(ProjectError,'endpoint'):search(data)


class EndpointDirectionTests(unittest.TestCase):
    def constrained(self):
        data=fixture();data['endpoint_directions']={role:dict(axis=axis,source='Explicit synthetic endpoint tangent',classification='design_choice') for role,axis in [('start',[0,1]),('end',[0,-1])]};return data
    def test_compiled_geometry_respects_both_requested_tangents(self):
        data=self.constrained();result=search(data);self.assertTrue(result['route_found']);self.assertEqual(result['pieces'][0]['start_m'],data['start_m']);self.assertEqual(result['pieces'][-1]['end_m'],data['end_m'])
        for role,piece in [('start',result['pieces'][0]),('end',result['pieces'][-1])]:
            self.assertEqual([round((piece['end_m'][i]-piece['start_m'][i])/piece['length_m']) for i in (0,1)],data['endpoint_directions'][role]['axis'])
    def test_impossible_heading_is_retained_as_no_path(self):
        data=self.constrained();data['endpoint_directions']['start']['axis']=[-1,0];r=search(data);self.assertFalse(r['route_found']);self.assertNotIn('pieces',r)
    def test_ambiguous_or_unsourced_directions_reject(self):
        for field,value in [('axis',[1,1]),('axis',[True,0]),('source',''),('classification','certified')]:
            data=self.constrained();data['endpoint_directions']['start'][field]=value
            with self.subTest(field=field),self.assertRaises(ProjectError):search(data)

    def test_local_frame_cannot_enter_world_xy_obstacle_extrusion(self):
        from bsa.route_obstacles import contract
        data=self.constrained();data['coordinate_plane']='declared-local-frame'
        with self.assertRaisesRegex(ProjectError,'World-XY'):contract(data,{})
