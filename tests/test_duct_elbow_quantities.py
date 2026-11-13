import copy
import math
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa import bim,duct_elbow_quantities as tool,duct_fitting_data as tables

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/rectangular-air/elbow-wall.json'


class DuctElbowQuantitiesTests(unittest.TestCase):
    def test_native_radius_profile_axis_flow_and_reynolds(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            folder=Path(folder);bim.run(EXAMPLE,folder/'native');model=ifcopenshell.open(str(folder/'native/model.ifc'));obj=model.by_type('IfcDuctFitting')[0];air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5)
            result=tool.calculate(obj,'in','out',.2,air);q=result['quantities'];self.assertAlmostEqual(q['bend_radial_internal_width_m'],.5);self.assertAlmostEqual(q['bend_normal_internal_height_m'],.3);self.assertAlmostEqual(q['bend_radius_over_radial_width'],1.6);self.assertAlmostEqual(q['bend_centerline_arc_length_m'],math.pi*.8/2)
            expected=1.2*(.2/(.5*.3))*(2*.5*.3/(.5+.3))/1.81e-5;self.assertAlmostEqual(q['bend_hydraulic_reynolds'],expected)
            changed=tool.calculate(obj,'in','out',.2,dict(density_kg_m3=1.2,viscosity_Pa_s=2*1.81e-5));self.assertAlmostEqual(changed['quantities']['bend_hydraulic_reynolds'],expected/2)
            body=next(r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body').Items[0];body.SweptArea.Position.Location.Coordinates=(.9,0.)
            with self.assertRaisesRegex(ValueError,'Axis differ'):tool.calculate(obj,'in','out',.2,air)

    def test_signed_bounded_three_axis_reynolds_control(self):
        # Fictional separable grid, not a publisher table or physical bend correlation.
        table=dict(axes=[dict(quantity='bend_radius_over_radial_width',values=[1.,2.]),dict(quantity='bend_height_over_radial_width',values=[.5,1.]),dict(quantity='bend_hydraulic_reynolds',values=[10000.,20000.])],coefficients=[[[.4,.2],[.8,.4]],[[.8,.4],[1.6,.8]]],conditions=[dict(quantity='bend_angle_deg',minimum=90.,maximum=90.)])
        query=dict(bend_radius_over_radial_width=1.5,bend_height_over_radial_width=.75,bend_hydraulic_reynolds=15000.,bend_angle_deg=90.)
        result=tables.lookup(table,query);self.assertAlmostEqual(result['coefficient'],.675)
        changed=copy.deepcopy(query);changed['bend_hydraulic_reynolds']=21000.;self.assertIsNone(tables.lookup(table,changed)['coefficient'])
        changed=copy.deepcopy(query);changed['bend_angle_deg']=45.;self.assertIsNone(tables.lookup(table,changed)['coefficient'])

    def test_nonquarter_and_invalid_air_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            folder=Path(folder);bim.run(EXAMPLE,folder/'native');model=ifcopenshell.open(str(folder/'native/model.ifc'));obj=model.by_type('IfcDuctFitting')[0]
            with self.assertRaises(ValueError):tool.calculate(obj,'in','out',.2,dict(density_kg_m3=1.2,viscosity_Pa_s=0))
            body=next(r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body').Items[0];body.Angle=math.pi/3
            with self.assertRaisesRegex(ValueError,'quarter'):tool.calculate(obj,'in','out',.2,dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5))


if __name__=='__main__':unittest.main()
