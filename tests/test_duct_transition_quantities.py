import json
import math
from pathlib import Path
import tempfile
import unittest

import ifcopenshell

from bsa.rectangular_transition import run
from bsa.duct_transition_quantities import calculate
from bsa.duct_fitting_data import flow_guard

ROOT = Path(__file__).resolve().parents[1]


class TransitionQuantityTests(unittest.TestCase):
    def test_native_stations_angles_direction_and_mutations(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for case in ('reduction','expansion','mixed_oblique','one_plane'):
                data=json.loads((ROOT/'examples/rectangular-transition/project.json').read_text())
                data['end_length_m']=.2
                if case=='expansion': data['start_section_m'],data['end_section_m']=data['end_section_m'],data['start_section_m']
                if case=='one_plane':data['end_section_m'][1]=data['start_section_m'][1]
                if case=='mixed_oblique':
                    data.update(start_section_m=[.5,.2],end_section_m=[.35,.3],upstream_angle_degrees=45.,transition_length_m=.075/math.tan(math.radians(22.5)))
                    data['placement'].update(origin_m=[12,-7,4],rotation=[[.6,0,.8],[0,1,0],[-.8,0,.6]])
                path=root/(case+'.json');path.write_text(json.dumps(data));out=root/case;run(path,out)
                model=ifcopenshell.open(str(out/'transition.ifc'));obj=model.by_type('IfcDuctFitting')[0]
                result=calculate(obj,'start','end');q=result['quantities']
                self.assertAlmostEqual(q['total_length_m'],.1+data['transition_length_m']+.2)
                self.assertAlmostEqual(q['taper_length_m'],data['transition_length_m'])
                self.assertAlmostEqual(q['inlet_straight_length_m'],.1);self.assertAlmostEqual(q['outlet_straight_length_m'],.2)
                self.assertAlmostEqual(q['major_taper_angle_deg'],data['upstream_angle_degrees'])
                for index,name in enumerate(('width','height')):
                    expected=math.degrees(2*math.atan(abs(data['end_section_m'][index]-data['start_section_m'][index])/(2*data['transition_length_m'])))
                    self.assertAlmostEqual(q['taper_'+name+'_angle_deg'],expected)
                w,h=data['end_section_m'];dh=2*w*h/(w+h)
                self.assertAlmostEqual(q['outlet_hydraulic_diameter_m'],dh)
                self.assertAlmostEqual(q['taper_length_over_outlet_hydraulic_diameter'],data['transition_length_m']/dh)
                self.assertGreater(q['total_length_over_outlet_hydraulic_diameter'],q['taper_length_over_outlet_hydraulic_diameter'])
                self.assertLess(result['inner_station_z_m'][0],result['outer_station_z_m'][0])
                self.assertEqual(result['flow_change'],dict(reduction='contraction',expansion='expansion',mixed_oblique='mixed_width_height_change',one_plane='contraction')[case])
                declared=dict(classification='published correlation',transition_flow_change=result['flow_change'])
                self.assertTrue(flow_guard(declared,result)['pass_check'])
                wrong=dict(declared,transition_flow_change='expansion' if result['flow_change']!='expansion' else 'contraction')
                self.assertFalse(flow_guard(wrong,result)['pass_check'])
                self.assertFalse(flow_guard(dict(classification='manufacturer data'),result)['pass_check'])
                self.assertIsNone(flow_guard(dict(classification='synthetic'),result)['pass_check'])
                reverse=calculate(obj,'end','start')
                self.assertAlmostEqual(reverse['quantities']['inlet_straight_length_m'],.2)
                self.assertAlmostEqual(reverse['quantities']['outlet_straight_length_m'],.1)
                self.assertEqual(reverse['inlet_section_m'],result['outlet_section_m'])
                self.assertEqual(reverse['flow_change'], 'expansion' if result['flow_change']=='contraction' else 'contraction' if result['flow_change']=='expansion' else 'mixed_width_height_change')
                self.assertEqual(flow_guard(declared,reverse)['pass_check'],result['flow_change']=='mixed_width_height_change')
                if result['flow_change']=='mixed_width_height_change':
                    for wrong_class in ('contraction','expansion'):
                        for geometry in (result,reverse):
                            self.assertFalse(flow_guard(dict(classification='published correlation',transition_flow_change=wrong_class),geometry)['pass_check'])
                with self.assertRaises(ValueError):calculate(obj,'start','start')
                wall=obj.Representation.Representations[0].Items[0]
                wall.Operator='UNION'
                with self.assertRaisesRegex(ValueError,'Outer-minus-inner'):calculate(obj,'start','end')
                wall.Operator='DIFFERENCE'
                p=wall.SecondOperand.Outer.CfsFaces[0].Bounds[0].Bound.Polygon[0];x,y,z=p.Coordinates;p.Coordinates=(x+.001,y,z)
                with self.assertRaises(ValueError):calculate(obj,'start','end')
