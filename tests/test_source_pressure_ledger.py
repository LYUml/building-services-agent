import copy
import unittest
from bsa.source_pressure_ledger import calculate
from bsa.duct_chain_analysis import boundary_paths


class PressureLedgerTests(unittest.TestCase):
    def test_reordered_disconnected_missing_boundary_and_wrong_owner_reject(self):
        for change in ('reverse','disconnect','boundary','owner'):
            case,data=self.fixture()
            if change=='reverse':case['boundary_paths'][0]['steps'].reverse()
            if change=='disconnect':case['interfaces'].pop()
            if change=='boundary':case['boundary_ports'].remove('b')
            if change=='owner':case['port_flows']['sout']['owner_guid']='wrong'
            with self.subTest(change=change),self.assertRaises(ValueError):calculate(case,data)

    def test_small_signed_subtotal_changes_are_not_hidden_by_absolute_floor(self):
        case,data=self.fixture();data['table_results'][0]['signed_tabulated_contribution_Pa']=-2e-12
        for row in data['boundary_paths']:
            row['supplied_table_contribution_Pa']=-2e-12
            if not row['unresolved_fitting_path_count']:row['tabulated_plus_separate_straight_Pa']=3.-2e-12
        self.assertEqual(calculate(case,data)['outlet_count'],2)
        data['boundary_paths'][0]['supplied_table_contribution_Pa']=-9e-12
        with self.assertRaisesRegex(ValueError,'subtotal differs'):calculate(case,data)

    def test_duplicate_unused_repeated_straights_and_boolean_counts_reject(self):
        for change in ('duplicate','unused','repeated','boolean'):
            case,data=self.fixture()
            if change=='duplicate':case['straight_sections'].append(dict(case['straight_sections'][0]))
            if change=='unused':case['straight_sections'].append(dict(guid='unused',straight_friction_Pa=1.))
            if change=='repeated':case['boundary_paths'][0]['steps'].insert(0,dict(case['boundary_paths'][0]['steps'][0]))
            if change=='boolean':data['boundary_paths'][1]['unresolved_fitting_path_count']=True
            with self.subTest(change=change),self.assertRaises(ValueError):calculate(case,data)

    def fixture(self):
        straight=dict(guid='s',straight_friction_Pa=3.)
        shared=dict(kind='fitting',product_guid='f',inlet_port_guid='in',outlet_port_guid='out')
        missing=dict(kind='fitting',product_guid='g',inlet_port_guid='gin',outlet_port_guid='b')
        main=dict(kind='fitting',product_guid='g',inlet_port_guid='gin',outlet_port_guid='a')
        ports={g:dict(owner_guid=owner,direction=direction,flow_m3_s=1. if g in ('a','b') else 2.) for g,owner,direction in [('root','s','SINK'),('sout','s','SOURCE'),('in','f','SINK'),('out','f','SOURCE'),('gin','g','SINK'),('a','g','SOURCE'),('b','g','SOURCE')]}
        case=dict(original_requirement_ids=['R'],port_flows=ports,products=[dict(guid=g) for g in ('s','f','g')],interfaces=[dict(source_port='sout',sink_port='in'),dict(source_port='out',sink_port='gin')],straight_sections=[straight],missing_fitting_path_losses=[shared,missing,main],boundary_ports=['root','a','b'])
        case['boundary_paths']=boundary_paths(ports,case['products'],case['interfaces'],[straight],case['missing_fitting_path_losses'],case['boundary_ports'])
        table={k:shared[k] for k in ('product_guid','inlet_port_guid','outlet_port_guid')};table.update(signed_tabulated_contribution_Pa=-2.,source_id='fictional',citation_location='Synthetic signed arithmetic control')
        zero={k:main[k] for k in ('product_guid','inlet_port_guid','outlet_port_guid')};zero.update(signed_tabulated_contribution_Pa=0.,source_id='fictional',citation_location='Synthetic zero control, not missing evidence')
        requests=[]
        for step,affected,value in [(shared,['a','b'],table),(missing,['b'],None),(main,['a'],zero)]:
            row={k:step[k] for k in ('product_guid','inlet_port_guid','outlet_port_guid')};row.update(recorded_table_result=value,affected_outlet_port_guids=affected,predefined_type='JUNCTION',status='source_data_required' if value is None else 'physical_review_required',required_evidence=['Fictional control only']);requests.append(row)
        data=dict(original_requirement_ids=['R'],data_requests=requests,table_results=[table,zero],boundary_paths=[dict(inlet_port_guid='root',outlet_port_guid=o,known_straight_friction_Pa=3.,supplied_table_contribution_Pa=-2.,unresolved_fitting_path_count=int(o=='b'),tabulated_plus_separate_straight_Pa=None if o=='b' else 1.,complete_total_pressure_drop_Pa=None) for o in 'ab'],transition_end_straight_study=[dict(friction_Pa=9999.)])
        return case,data

    def test_signed_parallel_paths_missing_and_excluded_end_studies(self):
        case,data=self.fixture();r=calculate(case,data)
        self.assertEqual(r['outlet_count'],2);self.assertEqual(r['conditional_numerical_path_count'],2)
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
