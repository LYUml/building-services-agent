from pathlib import Path
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import numpy as np

from bsa.circular_native import straight_wall
from bsa.engine import ProjectError


class NativeCircularCapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_route_join import RouteJoinTests
        cls.fixture=RouteJoinTests;cls.fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):cls.fixture.tearDownClass()

    def test_saved_wall_dimensions_and_both_cap_frames(self):
        model=ifcopenshell.open(str(self.fixture.joined))
        for obj in model.by_type('IfcDuctSegment'):
            record=straight_wall(obj)
            self.assertAlmostEqual(record['inner_m'],.2032)
            self.assertAlmostEqual(record['outer_m'],.2048)
            self.assertEqual(len(record['ports']),2)
            self.assertAlmostEqual(record['length_m'],4 if obj.Name=='ROUTE' else .3)

    def test_false_cap_at_correct_distance_and_wrong_normal_reject(self):
        for fault in ('station','normal'):
            model=ifcopenshell.open(str(self.fixture.joined));owner=model.by_guid(self.fixture.endpoints['start']['owner_guid'])
            port=next(p for p in system.get_ports(owner) if p.FlowDirection=='SINK')
            matrix=placement.get_local_placement(port.ObjectPlacement)
            if fault=='station':matrix[:3,3]=[0,.3,1.5]
            else:matrix[:3,:3]=np.eye(3)
            api.run('geometry.edit_object_placement',model,product=port,matrix=matrix,is_si=True)
            with self.subTest(fault=fault),self.assertRaises(ProjectError):straight_wall(owner)

    def test_wrong_units_or_unmatched_native_depth_rejects(self):
        for fault in ('units','depth'):
            model=ifcopenshell.open(str(self.fixture.joined));owner=model.by_guid(self.fixture.endpoints['start']['owner_guid'])
            if fault=='units':next(u for u in model.by_type('IfcSIUnit') if u.UnitType=='LENGTHUNIT').Prefix='MILLI'
            else:owner.Representation.Representations[0].Items[0].Depth=.4
            with self.subTest(fault=fault),self.assertRaises(ProjectError):straight_wall(owner)
