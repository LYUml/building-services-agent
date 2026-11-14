"""Actual host-selected network controls for logical versus physical interfaces."""
import copy
import json
import os
from pathlib import Path
import unittest
from bsa.duct_chain_analysis import boundary_paths
from bsa.source_pressure_ledger import calculate
from bsa.workspace import allowed


def load_folder(variable):
    path = Path(os.environ[variable]).resolve()
    if not allowed(path):
        raise ValueError('Fixture outside host-selected workspace')
    return path, json.loads((path/'analysis.json').read_text()), json.loads((path/'fitting-data.json').read_text())


@unittest.skipUnless(os.environ.get('BSA_LOGICAL_NETWORK_FIXTURE'), 'Host network not selected')
class ActualLogicalInterfaces(unittest.TestCase):
    def setUp(self):
        _, self.case, self.data = load_folder('BSA_LOGICAL_NETWORK_FIXTURE')

    def paths(self):
        c = self.case
        return boundary_paths(c['port_flows'], c['products'], c['interfaces'], c['straight_sections'], c['missing_fitting_path_losses'], c['boundary_ports'])

    def logical_row(self):
        return next(r for r in self.case['interfaces'] if r.get('interface_basis') == 'logical_equipment_connection')

    def test_actual_tree_keeps_physical_review_gates(self):
        result = calculate(self.case, self.data)
        self.assertEqual(result['outlet_count'], 80)
        self.assertEqual(result['logical_equipment_interface_count'], 120)
        self.assertFalse(result['physical_airway_continuity_verified'])
        self.assertEqual(result['conditional_numerical_path_count'], 194)
        self.assertEqual(result['numerically_unresolved_fitting_path_count'], 264)
        self.assertTrue(all(r['logical_equipment_interfaces_requiring_physical_review'] == 3 for r in result['outlet_paths']))
        self.assertTrue(all(r['complete_total_pressure_drop_Pa'] is None for r in result['outlet_paths']))

    def test_logical_connection_cannot_certify_material_caps(self):
        self.logical_row()['physical_cap_verified'] = True
        with self.assertRaises(ValueError): self.paths()

    def test_nonboolean_receipt_rejected(self):
        self.logical_row()['physical_cap_verified'] = 'false'
        with self.assertRaises(ValueError): self.paths()

    def test_missing_receipt_stays_not_verified(self):
        self.logical_row().pop('physical_cap_verified')
        paths = self.paths()
        self.assertEqual(paths, self.case['boundary_paths'])
        self.assertTrue(all(s['physical_cap_verified'] is False for p in paths for s in p['steps'] if s.get('interface_basis') == 'logical_equipment_connection'))

    def test_erased_path_evidence_rejected(self):
        step = next(s for p in self.case['boundary_paths'] for s in p['steps'] if s.get('interface_basis') == 'logical_equipment_connection')
        step.pop('physical_cap_verified')
        with self.assertRaises(ValueError): calculate(self.case, self.data)

    def test_unknown_device_areas_remain_unknown(self):
        ports = [p for p in self.case['port_flows'].values() if p.get('section_type') == 'equipment_internal_unknown']
        self.assertEqual(len(ports), 140)
        before = copy.deepcopy(self.case)
        calculate(self.case, self.data)
        self.assertEqual(self.case, before)
        self.assertTrue(all(p['actual_area_m2'] is None and p['actual_velocity_pressure_Pa'] is None for p in ports))

    @unittest.skipUnless(os.environ.get('BSA_MAIN_NETWORK_FIXTURE'), 'Host main-only fixture not selected')
    def test_unannotated_main_keeps_original_numeric_result(self):
        path, case, data = load_folder('BSA_MAIN_NETWORK_FIXTURE')
        self.assertEqual(calculate(case, data), json.loads((path/'pressure-ledger.json').read_text()))
