"""Opt-in native fixture controls; input supplied by the host, never a document."""
import math
import os
from pathlib import Path
import unittest
import ifcopenshell
from ifcopenshell.util import system
from bsa.rect_round_quantities import calculate
from bsa.workspace import allowed


class NativeRectRoundControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=os.environ.get('BSA_RECT_ROUND_FIXTURE')
        if not source:raise unittest.SkipTest('Explicit native fixture not configured')
        cls.path=Path(source).resolve()
        if not allowed(cls.path):raise ValueError('Host-selected fixture workspace required')

    def setUp(self):
        self.model=ifcopenshell.open(str(self.path))
        self.obj=self.model.by_type('IfcDuctFitting')[0]
        self.air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5)

    def test_rigid_placement_does_not_change_local_parameters(self):
        before=calculate(self.obj,.4,self.air)
        location=self.obj.ObjectPlacement.RelativePlacement.Location
        location.Coordinates=tuple(v+d for v,d in zip(location.Coordinates,[1.25,-2.,3.]))
        self.assertEqual(calculate(self.obj,.4,self.air)['source_quantities'],before['source_quantities'])
        self.assertFalse(before['physical_applicability_verified'])

    def test_moved_owned_port_rejected(self):
        port=next(p for p in system.get_ports(self.obj) if p.FlowDirection=='SOURCE')
        location=port.ObjectPlacement.RelativePlacement.Location
        values=list(location.Coordinates);values[2]+=.01;location.Coordinates=values
        with self.assertRaisesRegex(ValueError,'station/direction'):calculate(self.obj,.4,self.air)

    def test_nonruled_surface_rejected(self):
        item=self.obj.Representation.Representations[0].Items[0].MappingSource.MappedRepresentation.Items[0]
        surface=next(f.FaceSurface for f in item.FirstOperand.Outer.CfsFaces if f.FaceSurface.is_a('IfcBSplineSurfaceWithKnots'))
        surface.VDegree=2
        with self.assertRaisesRegex(ValueError,'degree-one'):calculate(self.obj,.4,self.air)

    def test_nonfinite_flow_rejected(self):
        with self.assertRaisesRegex(ValueError,'Finite positive'):calculate(self.obj,math.nan,self.air)

    def test_zero_surface_axis_rejected(self):
        item=self.obj.Representation.Representations[0].Items[0].MappingSource.MappedRepresentation.Items[0]
        surface=next(f.FaceSurface for f in item.FirstOperand.Outer.CfsFaces if f.FaceSurface.is_a('IfcCylindricalSurface'))
        surface.Position.Axis.DirectionRatios=(0.,0.,0.)
        with self.assertRaisesRegex(ValueError,'nonzero'):calculate(self.obj,.4,self.air)

    def test_nonmetre_model_rejected(self):
        unit=next(u for u in self.model.by_type('IfcSIUnit') if u.UnitType=='LENGTHUNIT')
        unit.Prefix='MILLI'
        with self.assertRaisesRegex(ValueError,'metre IFC4'):calculate(self.obj,.4,self.air)

    def test_missing_units_rejected(self):
        self.model.by_type('IfcProject')[0].UnitsInContext=None
        with self.assertRaisesRegex(ValueError,'metre IFC4'):calculate(self.obj,.4,self.air)
