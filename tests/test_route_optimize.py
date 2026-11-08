import json
import math
from pathlib import Path
import unittest

from bsa.engine import ProjectError
from bsa.route_optimize import select

ROOT=Path(__file__).resolve().parents[1]


class PressureRouteTests(unittest.TestCase):
    def setUp(self):
        root=ROOT/'examples/route-search'
        self.routing,self.settings,self.network=[json.loads((root/p).read_text()) for p in ('route-input.json','model-settings.json','network.json')]

    def test_lower_loss_route_has_two_bends_despite_longer_length(self):
        _,result=select(self.routing,self.settings,self.network)
        route=result['selected_route'];baseline=result['baseline_route']
        self.assertEqual(baseline['bend_count'],8)
        self.assertEqual(route['bend_count'],2)
        self.assertGreater(route['length_m'],baseline['length_m'])
        self.assertAlmostEqual(route['length_m'],6-.8+math.pi*.2)
        v=.0001/(math.pi*.08**2/4)
        expected=32*.001*route['length_m']*v/.08**2+.8*998*v*v/2
        self.assertAlmostEqual(result['selected_pressure']['segments'][0]['dissipative_loss_pa'],expected)
        self.assertGreater(result['pressure_reduction_pa'],.4)

    def test_additional_straight_piece_loss_is_included_in_objective(self):
        self.settings['straight_excess_k']=.3
        _,result=select(self.routing,self.settings,self.network)
        route=result['selected_route'];v=.0001/(math.pi*.08**2/4)
        expected=32*.001*route['length_m']*v/.08**2+(route['bend_count']*.4+(route['bend_count']+1)*.3)*998*v*v/2
        self.assertAlmostEqual(result['predicted_selected_loss_pa'],expected)

    def test_lower_pressure_does_not_turn_failed_target_into_acceptance(self):
        self.network['supply']['total_pressure_pa']=1
        _,result=select(self.routing,self.settings,self.network)
        self.assertGreater(result['pressure_reduction_pa'],0)
        self.assertFalse(result['calculated_checks_pass'])
        self.assertFalse(result['design_accepted'])

    def test_conflicting_objective_is_rejected(self):
        self.routing.update(bend_penalty_m=.1,objective_source='Other objective')
        with self.assertRaisesRegex(ProjectError,'second objective'):select(self.routing,self.settings,self.network)
