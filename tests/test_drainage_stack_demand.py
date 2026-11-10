import copy
import unittest
from bsa.drainage_stack_demand import calculate


class StackDemandTests(unittest.TestCase):
    def setUp(self):
        self.project = dict(scope=dict(building_storeys=21, stack_scope='building',
                            edition_basis='Synthetic', works_basis='Synthetic', evidence='Synthetic'),
                            inventory_complete=True, inventory_source='Synthetic restricted floors',
                            fixtures=[dict(id='WC0', floor_offset=0, connected_to_stack=False,
                                           separate_to_manhole=True, source='Synthetic'),
                                      dict(id='WC1', floor_offset=1, connected_to_stack=False,
                                           separate_to_manhole=True, source='Synthetic'),
                                      dict(id='WC2', floor_offset=2, connected_to_stack=True,
                                           separate_to_manhole=False, source='Synthetic')])
        self.basis = dict(fixture_units={name: dict(value=du, source='Synthetic DU', classification='assumed')
                                        for name, du in [('WC0', 8), ('WC1', 4), ('WC2', 2)]},
                          frequency_factor=dict(value=.5, source='Synthetic use', classification='assumed'),
                          full_stack_inventory_verified=True, frequency_classification_verified=True,
                          basis='Synthetic full-stack inventory, not a real building', references={})

    def test_independent_floor_exclusion_and_count(self):
        result = calculate(self.project, self.basis)
        self.assertEqual(result['included_fixture_ids'], ['WC2'])
        self.assertEqual(result['excluded_direct_manhole_fixture_ids'], ['WC0', 'WC1'])
        self.assertEqual(result['calculation']['total_DU'], 2)
        self.assertAlmostEqual(result['calculation']['wastewater_flow_L_s'], .5*2**.5)
        self.assertFalse(result['design_accepted'])

    def test_exact_inventory_coverage(self):
        for name in ('missing', 'extra'):
            basis = copy.deepcopy(self.basis)
            if name == 'missing': del basis['fixture_units']['WC2']
            else: basis['fixture_units']['UNKNOWN'] = basis['fixture_units']['WC2']
            with self.assertRaises(ValueError): calculate(self.project, basis)

    def test_failed_rule_blocks_math(self):
        self.project['fixtures'][1]['connected_to_stack'] = True
        result = calculate(self.project, self.basis)
        self.assertEqual(result['status'], 'fail')
        self.assertIsNone(result['calculation'])

    def test_unknown_full_inventory_and_upper_route(self):
        self.basis['full_stack_inventory_verified'] = None
        self.assertEqual(calculate(self.project, self.basis)['status'], 'pending')
        self.basis['full_stack_inventory_verified'] = True
        self.project['fixtures'][2]['connected_to_stack'] = None
        result = calculate(self.project, self.basis)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['unresolved_fixture_ids'], ['WC2'])
        self.assertIsNone(result['calculation'])

    def test_unknown_factor_or_empty_stack_cannot_claim_zero_capacity(self):
        self.basis['frequency_factor']['value'] = None
        self.assertEqual(calculate(self.project, self.basis)['status'], 'pending')
        self.basis['frequency_factor']['value'] = .5
        self.project['fixtures'][2].update(connected_to_stack=False, separate_to_manhole=True)
        result = calculate(self.project, self.basis)
        self.assertEqual(result['status'], 'pending')
        self.assertIsNone(result['calculation'])
