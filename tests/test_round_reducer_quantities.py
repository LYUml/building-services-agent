"""Opt-in native reducer mutation controls; private fixture is host-selected."""
import math
import os
import unittest
from pathlib import Path
import ifcopenshell
from bsa.round_reducer_quantities import calculate
from bsa.workspace import allowed


@unittest.skipUnless(os.environ.get('BSA_ROUND_REDUCER_FIXTURE'), 'Host native fixture not selected')
class NativeReducerControls(unittest.TestCase):
    def setUp(self):
        p = Path(os.environ['BSA_ROUND_REDUCER_FIXTURE']).resolve()
        if not allowed(p):
            raise ValueError('Fixture must be within host-selected workspace')
        self.model = ifcopenshell.open(str(p))
        self.obj = next(o for o in self.model.by_type('IfcDuctFitting') if o.Name.endswith('-REDUCER'))

    def test_reference_is_large_inlet(self):
        x = calculate(self.obj, .15, 1.2)
        self.assertAlmostEqual(x['inlet_velocity_pressure_Pa'], 1.2*(.15/(math.pi*.254**2/4))**2/2)
        self.assertAlmostEqual(x['inlet_to_outlet_area_ratio'], 1.5625)

    def test_partial_revolution_rejected(self):
        self.obj.Representation.Representations[0].Items[0].Angle = math.pi
        with self.assertRaises(ValueError): calculate(self.obj, .15, 1.2)

    def test_changed_profile_rejected(self):
        p = self.obj.Representation.Representations[0].Items[0].SweptArea.OuterCurve.Points[2]
        p.Coordinates = (p.Coordinates[0]+.001, p.Coordinates[1])
        with self.assertRaises(ValueError): calculate(self.obj, .15, 1.2)

    def test_displaced_port_rejected(self):
        from ifcopenshell.util.system import get_ports
        p = get_ports(self.obj)[0].ObjectPlacement.RelativePlacement.Location
        p.Coordinates = tuple(v+.01 for v in p.Coordinates)
        with self.assertRaises(ValueError): calculate(self.obj, .15, 1.2)

    def test_missing_units_rejected(self):
        self.model.by_type('IfcProject')[0].UnitsInContext = None
        with self.assertRaises(ValueError): calculate(self.obj, .15, 1.2)

    def test_nonmetre_units_rejected(self):
        units = self.model.by_type('IfcProject')[0].UnitsInContext.Units
        next(u for u in units if getattr(u, 'UnitType', None)=='LENGTHUNIT').Prefix = 'MILLI'
        with self.assertRaises(ValueError): calculate(self.obj, .15, 1.2)

    def test_nan_flow_rejected(self):
        with self.assertRaises(ValueError): calculate(self.obj, math.nan, 1.2)
