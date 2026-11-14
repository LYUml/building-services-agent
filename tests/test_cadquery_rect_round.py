import copy
import math
import unittest
from bsa.cadquery_rect_round import validate


class CadQueryInputTests(unittest.TestCase):
    def setUp(self):
        self.spec=dict(source='Synthetic validation control only',cases=[dict(id='case-01',width_m=.35,height_m=.3,
            diameter_m=.3048,section_offset_m=.0008,taper_length_m=.3,start_length_m=.05,end_length_m=.05)])

    def test_explicit_dimensions_accepted(self):
        self.assertEqual(validate(self.spec),self.spec)

    def test_paths_and_duplicate_id_rejected(self):
        for name in ['../escape','C:/outside','a/b','','CON','nul','LPT1']:
            spec=copy.deepcopy(self.spec);spec['cases'][0]['id']=name
            with self.assertRaisesRegex(ValueError,'path-safe'):validate(spec)
        self.spec['cases']*=2
        with self.assertRaisesRegex(ValueError,'path-safe'):validate(self.spec)

    def test_nonphysical_and_undeclared_inputs_rejected(self):
        for value in [0,-1,math.nan,math.inf,True]:
            spec=copy.deepcopy(self.spec);spec['cases'][0]['diameter_m']=value
            with self.assertRaisesRegex(ValueError,'Finite positive'):validate(spec)
        self.spec['cases'][0]['command']='ignored?'
        with self.assertRaisesRegex(ValueError,'Exact local'):validate(self.spec)

    def test_offset_and_missing_source_rejected(self):
        spec=copy.deepcopy(self.spec);spec['cases'][0]['section_offset_m']=.2
        with self.assertRaisesRegex(ValueError,'half each'):validate(spec)
        self.spec['source']=''
        with self.assertRaisesRegex(ValueError,'source'):validate(self.spec)
