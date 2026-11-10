import unittest
from bsa.air_load import calculate, UNITS


class AirLoadTests(unittest.TestCase):
    def inputs(self):
        values=dict(area=100,cooling_allowance=200,sensible_fraction=.8,
                    density=1.25,specific_heat=1000,temperature_difference=10)
        return {k:dict(value=v,unit=UNITS[k],source='Synthetic test',classification='assumed') for k,v in values.items()}

    def test_units_and_energy_balance(self):
        r=calculate(self.inputs())
        self.assertEqual(r['total_cooling_kW_thermal'],20)
        self.assertEqual(r['sensible_trial_kW_thermal'],16)
        self.assertEqual(r['supply_flow_m3_s'],1.28)
        self.assertEqual(r['supply_flow_L_s'],1280)
        self.assertFalse(r['room_sensible_load_verified'])
        self.assertFalse(r['design_accepted'])

    def test_invalid_inputs(self):
        for key,field,value in [('area','unit','ft2'),('sensible_fraction','value',1.1),('density','value',True),('temperature_difference','value',0),('specific_heat','value',float('inf')),('area','source',''),('area','classification','verified')]:
            data=self.inputs();data[key][field]=value
            with self.subTest(key=key,field=field),self.assertRaises(ValueError):calculate(data)

    def test_numerical_overflow_rejected(self):
        data=self.inputs();data['area']['value']=1e308
        with self.assertRaises(ValueError):calculate(data)
