"""Actual native bullhead family controls with an explicit host fixture."""
import os
from pathlib import Path
import unittest
import ifcopenshell
from ifcopenshell.util.system import get_ports
from bsa.workspace import allowed
from bsa.rectangular_tee_profiles import sections


@unittest.skipUnless(os.environ.get('BSA_BULLHEAD_FIXTURE'), 'Host native fixture not selected')
class BullheadProfiles(unittest.TestCase):
    def setUp(self):
        p = Path(os.environ['BSA_BULLHEAD_FIXTURE']).resolve()
        if not allowed(p): raise ValueError('Host-selected fixture workspace required')
        self.model = ifcopenshell.open(str(p))
        self.obj = next(o for o in self.model.by_type('IfcDuctFitting') if o.Name=='RECTANGULAR-BULLHEAD-TEE')

    def test_actual_area_sum(self):
        sizes = sections(self.obj, bullhead_area_sum=True)
        self.assertEqual(sizes[next(p.GlobalId for p in get_ports(self.obj) if p.Name=='branch')], [.65, .6])
        for p in get_ports(self.obj):
            if p.Name!='branch': self.assertEqual(sizes[p.GlobalId], [.325, .6])

    def test_default_family_stays_rejected(self):
        with self.assertRaises(ValueError): sections(self.obj)

    def test_wrong_flow_family_rejected(self):
        next(p for p in get_ports(self.obj) if p.Name=='branch').FlowDirection='SOURCE'
        with self.assertRaises(ValueError): sections(self.obj, bullhead_area_sum=True)

    def test_inexact_area_family_rejected(self):
        wall=self.obj.Representation.Representations[0].Items[0]
        wall.FirstOperand.FirstOperand.SweptArea.XDim+=.01
        wall.SecondOperand.FirstOperand.SweptArea.XDim+=.01
        with self.assertRaises(ValueError): sections(self.obj, bullhead_area_sum=True)

    def test_displaced_port_rejected(self):
        loc=get_ports(self.obj)[0].ObjectPlacement.RelativePlacement.Location
        loc.Coordinates=tuple(x+.01 for x in loc.Coordinates)
        with self.assertRaises(ValueError): sections(self.obj, bullhead_area_sum=True)

    def test_missing_units_rejected(self):
        self.model.by_type('IfcProject')[0].UnitsInContext=None
        with self.assertRaises(ValueError): sections(self.obj, bullhead_area_sum=True)

    def test_non_boolean_mode_rejected(self):
        with self.assertRaises(ValueError): sections(self.obj, bullhead_area_sum='yes')
