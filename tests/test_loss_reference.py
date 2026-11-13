import copy
import unittest
from bsa.loss_reference import rebase,compare


class LossReferenceTests(unittest.TestCase):
    def fixture(self):
        request=dict(product_guid='fictional',inlet_port_guid='in',outlet_port_guid='out',inlet=dict(flow_m3_s=2.,width_m=1.,height_m=1.,actual_velocity_m_s=2.,actual_velocity_pressure_Pa=2.),outlet=dict(flow_m3_s=2.,width_m=.5,height_m=1.,actual_velocity_m_s=4.,actual_velocity_pressure_Pa=8.),recorded_table_result=dict(reference_port_guid='in',coefficient=2.,reference_velocity_pressure_Pa=2.,signed_tabulated_contribution_Pa=4.))
        probe=dict(product_guid='fictional',status='bounded_numerical_crosscheck_only',candidate_coefficient=.5,candidate_signed_Pa=4.)
        return request,probe

    def test_signed_pressure_invariant_and_invalid_references(self):
        self.assertEqual(rebase(-.5,8.,2.),-2.)
        self.assertEqual(rebase(rebase(3.,2.,8.),8.,2.),3.)
        for args in [(1.,0.,2.),(1.,2.,-1.),(True,2.,3.),(float('nan'),2.,3.),(1.,float('inf'),3.)]:
            with self.assertRaises(ValueError):rebase(*args)

    def test_reference_change_explains_coefficients_but_not_different_pressures(self):
        request,probe=self.fixture();r=compare(request,probe)
        self.assertTrue(r['reference_conversion_removes_numeric_difference']);self.assertEqual(r['existing_coefficient_on_common_reference'],.5)
        probe.update(candidate_coefficient=1.,candidate_signed_Pa=8.)
        r=compare(request,probe);self.assertFalse(r['reference_conversion_removes_numeric_difference']);self.assertEqual(r['difference_Pa'],4.);self.assertFalse(r['physical_method_selected'])

    def test_wrong_owner_flow_density_and_stored_pressure_reject(self):
        for mutation in ('owner','flow','density','stored','reference'):
            request,probe=copy.deepcopy(self.fixture())
            if mutation=='owner':request['recorded_table_result']['reference_port_guid']='other'
            if mutation=='flow':request['outlet']['flow_m3_s']=3.
            if mutation=='density':request['outlet']['actual_velocity_pressure_Pa']=7.
            if mutation=='stored':probe['candidate_signed_Pa']=99.
            if mutation=='reference':request['recorded_table_result']['reference_velocity_pressure_Pa']=99.
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):compare(request,probe)
