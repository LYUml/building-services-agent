import copy
import unittest
from bsa.transition_straight_friction import calculate


class TransitionStraightTests(unittest.TestCase):
    def fixture(self):
        return dict(product_guid='fictional',geometry_sha256='0'*64,
            inlet_port_guid='a',outlet_port_guid='b',
            transition_geometry=dict(quantities=dict(inlet_straight_length_m=.1,outlet_straight_length_m=.2),
                inlet_section_m=[.6,.4],outlet_section_m=[.4,.3]),
            inlet=dict(width_m=.6,height_m=.4,flow_m3_s=1.),
            outlet=dict(width_m=.4,height_m=.3,flow_m3_s=1.))

    air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009)

    def test_lengths_sections_flow_and_no_pressure_release(self):
        request=self.fixture();original=copy.deepcopy(request);r=calculate(request,self.air)
        self.assertEqual(request,original)
        for row in r['ends']:
            c=row['calculation'];de=c['equivalent_diameter_m'];velocity=c['equivalent_round_velocity_m_s']
            expected=c['darcy_factor']*1.2*velocity**2*row['length_m']/(2*de)
            self.assertAlmostEqual(expected,row['developed_flow_study_friction_Pa'])
        self.assertFalse(r['added_to_pressure_paths']);self.assertFalse(r['physical_applicability_verified'])
        request['transition_geometry']['quantities']['inlet_straight_length_m']=0.
        self.assertEqual(calculate(request,self.air)['ends'][0]['developed_flow_study_friction_Pa'],0.)
        request['transition_geometry']['quantities']['outlet_straight_length_m']=.4
        self.assertAlmostEqual(calculate(request,self.air)['ends'][1]['developed_flow_study_friction_Pa'],2*r['ends'][1]['developed_flow_study_friction_Pa'])

    def test_invalid_geometry_and_nonconserved_flow_reject(self):
        for mutation in ('negative','nonfinite','dimension','flow','missing'):
            request=self.fixture()
            if mutation=='negative':request['transition_geometry']['quantities']['inlet_straight_length_m']=-.1
            if mutation=='nonfinite':request['transition_geometry']['quantities']['inlet_straight_length_m']=float('nan')
            if mutation=='dimension':request['inlet']['width_m']=.7
            if mutation=='flow':request['outlet']['flow_m3_s']=.9
            if mutation=='missing':request['transition_geometry']=None
            with self.assertRaises(ValueError):calculate(request,self.air)
