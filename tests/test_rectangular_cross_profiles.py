"""Host-selected native cross controls, not product acceptance."""
import os
from pathlib import Path
import unittest
import ifcopenshell
from ifcopenshell.util.system import get_ports
from bsa.workspace import allowed
from bsa.rectangular_cross_profiles import sections


@unittest.skipUnless(os.environ.get('BSA_CROSS_FIXTURE'), 'Native fixture not selected')
class CrossProfiles(unittest.TestCase):
    def setUp(self):
        p=Path(os.environ['BSA_CROSS_FIXTURE']).resolve()
        if not allowed(p): raise ValueError('Host-selected workspace required')
        self.model=ifcopenshell.open(str(p))
        self.obj=next(o for o in self.model.by_type('IfcDuctFitting') if o.Name=='RECTANGULAR-CROSS')

    def test_actual_sections(self):
        sizes=sections(self.obj)
        for p in get_ports(self.obj):self.assertEqual(sizes[p.GlobalId], [.65,.85] if p.Name.startswith('branch') else [.85,.85])

    def test_displaced_cap_rejected(self):
        p=get_ports(self.obj)[0].ObjectPlacement.RelativePlacement.Location
        p.Coordinates=tuple(v+.01 for v in p.Coordinates)
        with self.assertRaises(ValueError): sections(self.obj)

    def test_wrong_flow_family_rejected(self):
        next(p for p in get_ports(self.obj) if p.FlowDirection=='SOURCE').FlowDirection='SINK'
        with self.assertRaises(ValueError): sections(self.obj)

    def test_unequal_heights_rejected(self):
        wall=self.obj.Representation.Representations[0].Items[0]
        for u in [wall.FirstOperand,wall.SecondOperand]:u.SecondOperand.SweptArea.YDim+=.01
        with self.assertRaises(ValueError): sections(self.obj)

    def test_nonmetre_model_rejected(self):
        next(u for u in self.model.by_type('IfcProject')[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT').Prefix='MILLI'
        with self.assertRaises(ValueError): sections(self.obj)

    def test_missing_units_rejected(self):
        self.model.by_type('IfcProject')[0].UnitsInContext=None
        with self.assertRaises(ValueError): sections(self.obj)

    def test_wrong_operand_placement_rejected(self):
        p=self.obj.Representation.Representations[0].Items[0].SecondOperand.SecondOperand.Position.Location
        p.Coordinates=tuple(v+.01 for v in p.Coordinates)
        with self.assertRaises(ValueError): sections(self.obj)
