import math
import unittest

import ifcopenshell

from bsa.cfd_air_domain import air_item


class AirDomainTests(unittest.TestCase):
    def setUp(self):
        self.f = ifcopenshell.file(schema='IFC4')
        self.length = self.f.create_entity('IfcSIUnit', UnitType='LENGTHUNIT', Name='METRE')
        self.angle = self.f.create_entity('IfcSIUnit', UnitType='PLANEANGLEUNIT', Name='RADIAN')
        self.units = self.f.create_entity('IfcUnitAssignment', Units=[self.length, self.angle])
        p = self.f.create_entity('IfcRectangleHollowProfileDef', ProfileType='AREA', XDim=1.002,
                                YDim=.502, WallThickness=.001)
        self.solid = self.f.create_entity('IfcExtrudedAreaSolid', SweptArea=p, Depth=2.,
            ExtrudedDirection=self.f.create_entity('IfcDirection', DirectionRatios=(0., 0., 1.)))

    def test_clear_section_preserves_extrusion(self):
        air = air_item(self.f, self.solid)
        self.assertAlmostEqual(air.SweptArea.XDim, 1.)
        self.assertAlmostEqual(air.SweptArea.YDim, .5)
        self.assertEqual(air.Depth, 2.)
        self.assertEqual(air.ExtrudedDirection, self.solid.ExtrudedDirection)

    def test_missing_and_scaled_units_rejected(self):
        self.units.Units = [self.angle]
        with self.assertRaises(ValueError):
            air_item(self.f, self.solid)
        self.units.Units = [self.length, self.angle]
        self.length.Prefix = 'MILLI'
        with self.assertRaises(ValueError):
            air_item(self.f, self.solid)

    def test_invalid_depth_or_bore_rejected(self):
        self.solid.Depth = 0.
        with self.assertRaises(ValueError):
            air_item(self.f, self.solid)
        self.solid.Depth = 2.
        self.solid.SweptArea.WallThickness = 1.
        with self.assertRaises(ValueError):
            air_item(self.f, self.solid)

    def test_revolution_requires_unscaled_radians(self):
        origin = self.f.create_entity('IfcCartesianPoint', Coordinates=(0., 0., 0.))
        axis = self.f.create_entity('IfcAxis1Placement', Location=origin)
        solid = self.f.create_entity('IfcRevolvedAreaSolid', SweptArea=self.solid.SweptArea,
                                     Axis=axis, Angle=math.pi/2)
        self.assertEqual(air_item(self.f, solid).Angle, math.pi/2)
        self.angle.Prefix = 'MILLI'
        with self.assertRaises(ValueError):
            air_item(self.f, solid)


if __name__ == '__main__':
    unittest.main()
