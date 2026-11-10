import unittest
import ezdxf
from bsa.duct_plan_clearance import inspect


class PlanClearanceTests(unittest.TestCase):
    def fixture(self,units=6,lower=.25):
        d=ezdxf.new();d.units=units;factor=1000 if units==4 else 1;m=d.modelspace()
        line=m.add_line((0,0),(2*factor,0))
        coords=[(.5,lower),(1.5,lower),(1.5,lower+1),(.5,lower+1)]
        poly=m.add_lwpolyline([(x*factor,y*factor) for x,y in coords],close=True)
        schedule=dict(status='pass',sections=[dict(id='S',inputs=dict(width_m=1),calculation={'selected':True},failures=[])])
        binding=dict(sections={'S':dict(line_handle=line.dxf.handle,from_m=[0,0,0],to_m=[2,0,0])})
        spec=dict(drawing_sha256='Synthetic',schedule_sha256='Synthetic',binding_sha256='Synthetic',clearance_m=0,
                  basis='Synthetic nominal plan screen only',obstacles=[dict(id='COLUMN',polygon_m=coords,source_handles=[poly.dxf.handle],source='Synthetic actual drawing outline')])
        return d,schedule,binding,spec

    def test_overlap_area_and_millimetre_units(self):
        for units in (6,4):
            result=inspect(*self.fixture(units=units))
            self.assertAlmostEqual(result['checks'][0]['overlap_area_m2'],.25)
            self.assertEqual(result['checks'][0]['status'],'projected_overlap')
            self.assertFalse(result['planar_target_met'])
            self.assertFalse(result['design_accepted'])

    def test_contact_and_clearance_are_distinct(self):
        self.assertEqual(inspect(*self.fixture(lower=.5))['checks'][0]['status'],'touching')
        data=self.fixture(lower=.75)
        result=inspect(*data);self.assertAlmostEqual(result['checks'][0]['distance_m'],.25)
        self.assertTrue(result['planar_target_met'])
        self.assertEqual(result['status'],'review_required')
        data[3]['clearance_m']=.3
        self.assertEqual(inspect(*data)['checks'][0]['status'],'below_planar_target')

    def test_changed_source_polygon_line_and_failed_schedule_rejected(self):
        for case in ('polygon','line','schedule','duplicate','open_outline'):
            data=self.fixture()
            if case=='polygon':data[3]['obstacles'][0]['polygon_m'][0]=(0,.25)
            elif case=='line':data[0].entitydb[data[2]['sections']['S']['line_handle']].dxf.end=(3,0,0)
            elif case=='schedule':data[1]['sections'][0]['calculation']=None
            elif case=='duplicate':data[3]['obstacles'].append(dict(data[3]['obstacles'][0]))
            else:data[0].entitydb[data[3]['obstacles'][0]['source_handles'][0]].closed=False
            with self.assertRaises(ValueError):inspect(*data)
