import copy
import unittest
from bsa.source_network_schedule import build_tables,render


class NativeScheduleTests(unittest.TestCase):
    def fixture(self):
        # Fictional transformation controls; no engineering-source acceptance.
        products=[dict(guid=g,ifc_class='IfcDuctSegment' if g=='a' else 'IfcDuctFitting') for g in 'abc']
        products[2]['transition_geometry']=dict(quantities=dict(total_length_m=.75))
        ports={g+'-'+end:dict(owner_guid=g,direction='SINK' if end=='in' else 'SOURCE',source_section='S',source_node='J',flow_m3_s=1.,classification='synthetic design flow',width_m=.5,height_m=.4,actual_velocity_m_s=5.,actual_velocity_pressure_Pa=15.) for g in 'abc' for end in ('in','out')}
        case=dict(products=products,port_flows=ports,boundary_ports=['a-in','c-out'],straight_sections=[dict(guid='a',length_m=3.,straight_friction_Pa=1.2)],original_requirement_ids=['R1','R2','R3'])
        identities={g:dict(name='<script>same</script>',ifc_class=p['ifc_class'],predefined_type='STRAIGHT' if g=='a' else 'JUNCTION',source_properties={}) for g,p in zip('abc',products)}
        value=dict(coefficient=-.2,signed_tabulated_contribution_Pa=-3.,reference_port_guid='b-in',citation_location='Fictional source',applicability_note='Unaccepted control only')
        data=dict(data_requests=[dict(product_guid=g,inlet_port_guid=g+'-in',outlet_port_guid=g+'-out',status='physical_review_required' if g=='b' else 'source_data_required',recorded_table_result=value if g=='b' else None,required_evidence=['Fictional missing input']) for g in 'bc'])
        return case,data,identities

    def test_unique_model_keys_nulls_signed_values_sources_and_escaping(self):
        case,data,identities=self.fixture();before=copy.deepcopy(case)
        r=build_tables(case,data,identities,['ABSORBED']);self.assertEqual(case,before)
        self.assertEqual([p['tag'] for p in r['components']],['N001','N002','N003'])
        self.assertEqual(len(r['ports']),6);self.assertIsNone(r['components'][1]['model_path_length_m'])
        self.assertEqual(r['components'][2]['model_path_length_m'],.75)
        self.assertEqual(r['fitting_paths'][0]['conditional_signed_contribution_pa'],-3.)
        self.assertIsNone(r['fitting_paths'][1]['conditional_coefficient'])
        self.assertEqual(r['absorbed_source_sections'],['ABSORBED']);self.assertEqual(r['original_requirement_ids'],case['original_requirement_ids'])
        self.assertFalse(r['pressure_budget_complete']);self.assertFalse(r['design_accepted'])
        page=render(r);self.assertIn('&lt;script&gt;',page);self.assertNotIn('<script>',page)
        self.assertIn('Reference model ID',page)
        case['products'].reverse();self.assertEqual(build_tables(case,data,identities,['ABSORBED']),r)

    def test_duplicate_identity_path_wrong_owner_and_flow_mismatch_reject(self):
        for mutation in ('identity','path','owner','flow'):
            case,data,identities=self.fixture()
            if mutation=='identity':case['products'].append(copy.deepcopy(case['products'][0]))
            if mutation=='path':data['data_requests'].append(copy.deepcopy(data['data_requests'][0]))
            if mutation=='owner':data['data_requests'][0]['inlet_port_guid']='c-in'
            if mutation=='flow':case['port_flows']['a-out']['flow_m3_s']=2.
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):build_tables(case,data,identities,[])
