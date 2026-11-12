import copy
import math
from pathlib import Path
import json
import unittest

import manifold3d as m
import numpy as np

from bsa.engine import ProjectError
from bsa.route_material import evaluate, validate

ROOT=Path(__file__).resolve().parents[1]


class RouteMaterialTests(unittest.TestCase):
    def setUp(self):
        self.policy=json.loads((ROOT/'examples/route-search/material-qa-policy.json').read_text())
        self.tube=m.Manifold.cylinder(.3,.11,circular_segments=128)-m.Manifold.cylinder(.3,.1,circular_segments=128)
        self.solids={'first':self.tube,'second':self.tube.translate((0,0,.3))}
        frame=np.eye(4);frame[2,3]=.3
        self.interfaces=[dict(ports=['first.out','second.in'],bore_m=.2,frame=frame.tolist())]
        self.volume=math.pi*(.11**2-.1**2)*.6

    def test_connected_hollow_material_passes_without_engineering_acceptance(self):
        result=evaluate(self.solids,self.interfaces,self.volume,2,self.policy)
        self.assertTrue(result['calculated_checks_pass'])
        self.assertFalse(result['design_accepted'])
        self.assertEqual(result['union_components'],1)
        self.assertEqual(result['euler_characteristic'],0)
        self.assertEqual(len(result['probes']),1)

    def test_gap_and_overlap_fail_distinct_geometry_checks(self):
        for station,check in [(.31,'one_connected_material'),(.29,'no_material_interpenetration')]:
            solids=dict(self.solids,second=self.tube.translate((0,0,station)))
            result=evaluate(solids,self.interfaces,self.volume,2,self.policy)
            with self.subTest(station=station):
                self.assertFalse(result['checks'][check])
                self.assertFalse(result['calculated_checks_pass'])

    def test_centre_plug_fails_probe_and_bore_topology(self):
        plug=m.Manifold.cylinder(.002,.1,circular_segments=128,center=True).translate((0,0,.3))
        result=evaluate(dict(self.solids,plug=plug),self.interfaces,self.volume+math.pi*.1**2*.002,2,self.policy)
        self.assertFalse(result['checks']['sampled_centre_bore_clear'])
        self.assertFalse(result['checks']['two_boundary_bore_topology'])
        self.assertFalse(result['calculated_checks_pass'])

    def test_wrong_independent_volume_cannot_pass(self):
        result=evaluate(self.solids,self.interfaces,self.volume*1.1,2,self.policy)
        self.assertFalse(result['checks']['independent_volume'])
        self.assertFalse(result['calculated_checks_pass'])

    def test_policy_cannot_waive_material_interference_or_use_large_probe(self):
        policy=copy.deepcopy(self.policy);policy['overlap_volume_tolerance_m3']=1
        with self.assertRaises(ProjectError):validate(policy)
        policy=copy.deepcopy(self.policy);policy['probe_half_length_m']=.1
        with self.assertRaises(ProjectError):evaluate(self.solids,self.interfaces,self.volume,2,policy)
