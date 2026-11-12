import copy
import json
from pathlib import Path
import unittest

from bsa import pump_catalogue_iteration as selection,pump_electrical

ROOT=Path(__file__).resolve().parents[1]


class PumpElectricalCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.baseline=json.loads((ROOT/'examples/water-riser/electrical.json').read_text())
        self.link=json.loads((ROOT/'examples/water-riser/pump-electrical-link.json').read_text())
        self.context=(self.baseline,self.link)

    def summary(self,power):
        return dict(status='converged',calculated_checks_pass=True,checks={'synthetic_hydraulic_checks':True},
            operating_point=dict(estimated_electrical_kw=power))

    def test_electrical_current_limits_reject_hydraulic_pass_without_mutating_baseline(self):
        before=copy.deepcopy(self.baseline)
        low=selection.eligibility(self.summary(.44),self.context)
        high=selection.eligibility(self.summary(4),self.context)
        self.assertTrue(low['calculated_checks_pass']);self.assertFalse(high['calculated_checks_pass'])
        self.assertTrue(high['numerical_checks_pass']);self.assertEqual(high['electrical']['status'],'fail')
        circuit=next(c for c in low['electrical']['circuits'] if c['id']=='PUMP-SUPPLY')
        self.assertAlmostEqual(circuit['design_current_a'],.44*1000/.85/230)
        self.assertEqual(self.baseline,before)

    def test_preferred_unknown_efficiency_blocks_fallback_but_lower_unknown_does_not(self):
        options=[dict(id='unknown',source='Synthetic absent efficiency control',preference=0),dict(id='known',source='Synthetic known operating input',preference=1)]
        def evaluate(row,name):return selection.eligibility(self.summary(None if row['id']=='unknown' else .44),self.context)
        result=selection.preference.screen(options,evaluate)
        self.assertEqual(result['status'],'pending');self.assertEqual(result['unresolved_preference'],['unknown'])
        self.assertIsNone(result['selected']);self.assertTrue(result['feasible_candidate_found'])
        options[0]['preference']=2
        self.assertEqual(selection.preference.screen(options,evaluate)['selected']['id'],'known')

    def test_same_projection_preserves_hardware_other_devices_and_source_input(self):
        before=copy.deepcopy(self.baseline)
        revised=pump_electrical.operating_project(self.baseline,self.link,dict(estimated_electrical_kw=.44),'Explicit synthetic unit-test source')
        self.assertEqual(self.baseline,before);self.assertEqual(revised['circuits'],before['circuits'])
        for old,new in zip(before['devices'],revised['devices']):
            if old['id']!=self.link['electrical_device_id']:self.assertEqual(old,new)
        self.assertEqual(before['devices'][0]['electrical_kw'],.75)
        self.assertEqual(revised['devices'][0]['electrical_kw'],.44)


if __name__=='__main__':unittest.main()
