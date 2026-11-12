import copy
import unittest
from shapely.geometry import Point,Polygon
from bsa.air_load import calculate
from bsa.spatial_terminal_search import prepare

class TerminalSearchTests(unittest.TestCase):
    def fixture(self):
        inputs={k:dict(value=v,unit=u,source='Explicit synthetic search control',classification='assumed') for k,v,u in [('area',24,'m2'),('cooling_allowance',200,'W/m2'),('sensible_fraction',.8,'1'),('density',1.25,'kg/m3'),('specific_heat',1000,'J/(kg K)'),('temperature_difference',10,'K')]}
        balance=dict(calculation=dict(room_balances={'R':calculate(inputs)}));producer=dict(payload_schema='bsa.spatial-polygons/1',payload=dict(spaces=[dict(id='R',boundary_vertices=[[0,0],[6,0],[6,4],[0,4]])]))
        old=dict(calculation=dict(rooms={'R':dict(allocation=dict(terminals=[dict(id='old')]),design_basis=dict(turndown=dict(value=.4,unit='1',source='Synthetic turndown',classification='design_choice')))}))
        rows=[dict(flow_L_s=q,T025_m=t,static_pressure_Pa=1,total_pressure_Pa=2,NC=None,NC_qualifier='Synthetic unknown') for q,t in [(33,1),(297,5)]];selected={'old':dict(catalogue=dict(rows=rows))}
        policy=dict(grids=dict(value=[[1,1],[2,1],[1,2],[2,2]],source='Synthetic bounded search',classification='design_choice'),objective=dict(value='fewest_terminals_with_catalogue_coverage',source='Explicit synthetic comparison objective',classification='design_choice'),product_from_terminal={'R':'old'})
        return balance,producer,old,selected,policy
    def test_automatic_count_positions_and_rejected_original_preserve_flow(self):
        args=self.fixture();original=copy.deepcopy(args);r=prepare(*args)
        self.assertEqual(r['status'],'candidate_available');self.assertEqual(len(r['basis']['R']['terminals']),2);self.assertEqual(r['rooms']['R']['selected_grid_index'],1)
        self.assertEqual(r['rooms']['R']['attempts'][0]['reason'],'operating_flow_outside_catalogue')
        cases=r['rooms']['R']['attempts'][1]['cases'];self.assertAlmostEqual(sum(c['flow_L_s'] for c in cases if c['condition']=='maximum'),307.2)
        self.assertEqual(args,original);self.assertFalse(r['design_accepted'])
    def test_infeasible_policy_never_publishes_partial_or_clamped_candidate(self):
        args=self.fixture();args[-1]['grids']['value']=[[1,1]];r=prepare(*args)
        self.assertEqual(r['status'],'no_feasible_candidate');self.assertIsNone(r['basis']);self.assertIsNone(r['product_inheritance']);self.assertGreater(r['rooms']['R']['attempts'][0]['outside_catalogue_cases'],0)
    def test_concave_boundary_and_invalid_sources(self):
        args=self.fixture();points=[[0,0],[4,0],[4,2],[2,2],[2,6],[0,6]];args[1]['payload']['spaces'][0]['boundary_vertices']=points;r=prepare(*args)
        for t in r['basis']['R']['terminals']:self.assertTrue(Polygon(points).contains(Point(t['center_m'])))
        for field,value in [('product_from_terminal',{'R':'wrong-room'}),('grids',dict(value=[[0,1]],source='control',classification='design_choice'))]:
            bad=copy.deepcopy(args);bad[-1][field]=value
            with self.assertRaises(ValueError):prepare(*bad)

    def test_minimum_flow_cannot_be_ignored_by_count_search(self):
        args=self.fixture();args[2]['calculation']['rooms']['R']['design_basis']['turndown']['value']=.05
        r=prepare(*args);self.assertEqual(r['status'],'no_feasible_candidate')
        self.assertTrue(any(c['condition']=='minimum' and c['status']=='outside_catalogue' for a in r['rooms']['R']['attempts'] for c in a['cases']))
    def test_search_objective_must_be_an_explicit_design_choice(self):
        args=self.fixture();args[-1]['objective']['classification']='assumed'
        with self.assertRaises(ValueError):prepare(*args)
