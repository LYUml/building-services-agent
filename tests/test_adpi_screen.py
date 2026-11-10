import unittest
from bsa.adpi_screen import screen


class ADPIScreenTests(unittest.TestCase):
    def setUp(self):
        self.lookup=dict(terminals=[dict(id='T',directions=dict(east=dict(cases={k:dict(ratio=r,status='within_catalogue') for k,r in [('maximum',3.4),('minimum',1.)]})))])
        self.criterion=dict(source='Synthetic criterion fixture, not regulation',room_load_range_W_m2=[35,160],ratio_range=[1,3.4])
        self.facts={k:True for k in ('room_load_verified','product_category_verified','lengths_verified','installation_verified','edition_selected')}
    def evaluate(self,load=100):return screen(self.lookup,criterion=self.criterion,room_load_W_m2=load,facts=self.facts)
    def test_inclusive_boundaries_and_no_ADPI_claim(self):
        for load in [35,160]:
            r=self.evaluate(load);self.assertTrue(r['all_ratios_within_scope']);self.assertFalse(r['ADPI_verified'])
    def test_unverified_trial_load_cannot_pass(self):
        self.facts['room_load_verified']=None;r=self.evaluate(170.1)
        self.assertEqual(r['applicability'],'pending');self.assertFalse(r['load_in_source_range']);self.assertFalse(r['all_ratios_within_scope'])
    def test_known_outside_load_and_rejected_category(self):
        self.assertEqual(self.evaluate(170.1)['applicability'],'inapplicable')
        self.facts['product_category_verified']=False;self.assertEqual(self.evaluate()['applicability'],'inapplicable')
    def test_minimum_flow_failure_is_retained(self):
        self.lookup['terminals'][0]['directions']['east']['cases']['minimum']['ratio']=.9
        r=self.evaluate();self.assertFalse(r['all_ratios_within_scope']);self.assertEqual(r['cases'][1]['status'],'fail')
    def test_no_extrapolated_or_unknown_case_pass(self):
        self.lookup['terminals'][0]['directions']['east']['cases']['minimum'].update(ratio=None,status='outside_catalogue')
        self.assertFalse(self.evaluate()['all_ratios_within_scope'])
        with self.assertRaises(ValueError):self.evaluate(float('nan'))
