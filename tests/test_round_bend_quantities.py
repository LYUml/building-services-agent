"""Opt-in mutation controls on a host-selected actual native branch model."""
import math
import os
from pathlib import Path
import unittest
import ifcopenshell
from ifcopenshell.util import system
from bsa.round_bend_quantities import calculate
from bsa.workspace import allowed


@unittest.skipUnless(os.environ.get('BSA_ROUND_BEND_FIXTURE'), 'Host native fixture not selected')
class NativeRoundBendControls(unittest.TestCase):
    def setUp(self):
        p = Path(os.environ['BSA_ROUND_BEND_FIXTURE']).resolve()
        if not allowed(p):
            raise ValueError('Fixture outside selected workspace')
        self.model = ifcopenshell.open(str(p))
        self.obj = next(o for o in self.model.by_type('IfcDuctFitting') if o.Name.endswith('/plan-bend'))
        self.solid = self.obj.Representation.Representations[0].Items[0]

    def test_actual_minor_and_quarter_bends(self):
        bends = [o for o in self.model.by_type('IfcDuctFitting') if o.Name.endswith(('/plan-bend', '/terminal-bend'))]
        self.assertEqual(len(bends), 160)
        for o in bends:
            x = calculate(o)
            self.assertAlmostEqual(x['inner_m'], .2032)
            self.assertAlmostEqual(x['radius_m'], .3048)
            self.assertIsNone(x['pressure_loss_Pa'])
            self.assertFalse(x['physical_applicability_verified'])

    def test_major_arc_rejected(self):
        self.solid.Angle = math.pi
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_zero_angle_rejected(self):
        self.solid.Angle = 0.
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_displaced_cap_rejected(self):
        p = system.get_ports(self.obj)[0].ObjectPlacement.RelativePlacement.Location
        p.Coordinates = tuple(v+.01 for v in p.Coordinates)
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_axis_radius_mismatch_rejected(self):
        self.solid.SweptArea.Position.Location.Coordinates = (.4, 0.)
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_changed_axis_points_rejected(self):
        axis = next(r for r in self.obj.Representation.Representations if r.RepresentationIdentifier == 'Axis')
        pts = list(axis.Items[0].Points.CoordList)
        pts[1] = [v+.01 for v in pts[1]]
        axis.Items[0].Points.CoordList = pts
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_reverse_direction_rejected(self):
        system.get_ports(self.obj)[0].FlowDirection = 'SOURCE'
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_missing_units_rejected(self):
        self.model.by_type('IfcProject')[0].UnitsInContext = None
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_nonmetre_units_rejected(self):
        units = self.model.by_type('IfcProject')[0].UnitsInContext.Units
        next(u for u in units if getattr(u, 'UnitType', None) == 'LENGTHUNIT').Prefix = 'MILLI'
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_nonarea_profile_rejected(self):
        self.solid.SweptArea.ProfileType = 'CURVE'
        with self.assertRaises(ValueError): calculate(self.obj)

    def test_degree_units_rejected(self):
        import ifcopenshell.api as api
        degree = api.run('unit.add_conversion_based_unit', self.model, name='degree')
        context = self.model.by_type('IfcProject')[0].UnitsInContext
        context.Units = [u for u in context.Units if getattr(u, 'UnitType', None) != 'PLANEANGLEUNIT'] + [degree]
        with self.assertRaises(ValueError): calculate(self.obj)
