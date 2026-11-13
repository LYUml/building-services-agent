import copy
import unittest
from bsa.source_pressure_ledger import calculate


class PressureLedgerTests(unittest.TestCase):
    def fixture(self):
        straight=dict(kind='straight',product_guid='s',straight_friction_Pa=3.)
        shared=dict(kind='fitting',product_guid='f',inlet_port_guid='in',outlet_port_guid='out')
        missing=dict(kind='fitting',product_guid='g',inlet_port_guid='gin',outlet_port_guid='gout')
        case=dict(original_requirement_ids=['R'],straight_sections=[dict(guid='s',straight_friction_Pa=3.)],boundary_paths=[dict(inlet_port_guid='root',outlet_port_guid=o,steps=[straight,shared]+([missing] if o=='b' else []),known_straight_friction_Pa=3.) for o in 'ab'])
        table={k:shared[k] for k in ('product_guid','inlet_port_guid','outlet_port_guid')};table.update(signed_tabulated_contribution_Pa=-2.,source_id='fictional',citation_location='Synthetic signed arithmetic control')
        requests=[]
        for step,affected,value in [(shared,['a','b'],table),(missing,['b'],None)]:
            row={k:step[k] for k in ('product_guid','inlet_port_guid','outlet_port_guid')};row.update(recorded_table_result=value,affected_outlet_port_guids=affected,predefined_type='JUNCTION',status='source_data_required' if value is None else 'physical_review_required',required_evidence=['Fictional control only']);requests.append(row)
        data=dict(original_requirement_ids=['R'],data_requests=requests,table_results=[table],boundary_paths=[dict(inlet_port_guid='root',outlet_port_guid=o,known_straight_friction_Pa=3.,supplied_table_contribution_Pa=-2.,unresolved_fitting_path_count=int(o=='b'),tabulated_plus_separate_straight_Pa=None if o=='b' else 1.,complete_total_pressure_drop_Pa=None) for o in 'ab'],transition_end_straight_study=[dict(friction_Pa=9999.)])
        return case,data

    def test_signed_parallel_paths_missing_and_excluded_end_studies(self):
        case,data=self.fixture();r=calculate(case,data)
        self.assertEqual(r['outlet_count'],2);self.assertEqual(r['conditional_numerical_path_count'],1)
        self.assertEqual(r['outlet_paths'][0]['conditional_arithmetic_only_Pa'],1.)
        self.assertIsNone(r['outlet_paths'][1]['conditional_arithmetic_only_Pa'])
        self.assertEqual(r['missing_evidence_by_outlet_coverage'][0]['affected_outlet_port_guids'],['b'])
        self.assertIsNone(r['critical_path']);self.assertIsNone(r['fan_duty_Pa']);self.assertFalse(r['pressure_budget_complete'])
        self.assertEqual(r['excluded_transition_end_straight_study_count'],1)

    def test_wrong_coverage_duplicate_identity_and_fabricated_totals_reject(self):
        for change in ('affected','duplicate','subtotal','nan','request','complete','requirements'):
            case,data=copy.deepcopy(self.fixture())
            if change=='affected':data['data_requests'][0]['affected_outlet_port_guids']=['a']
            if change=='duplicate':data['data_requests'].append(copy.deepcopy(data['data_requests'][0]))
            if change=='subtotal':data['boundary_paths'][0]['supplied_table_contribution_Pa']=0.
            if change=='nan':data['table_results'][0]['signed_tabulated_contribution_Pa']=float('nan')
            if change=='request':data['data_requests'].pop()
            if change=='complete':data['boundary_paths'][0]['complete_total_pressure_drop_Pa']=1.
            if change=='requirements':data['original_requirement_ids']=[]
            with self.subTest(change=change),self.assertRaises(ValueError):calculate(case,data)
