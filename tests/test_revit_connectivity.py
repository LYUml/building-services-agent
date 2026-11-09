"""Synthetic fault injection only; does not substitute for running Revit."""
import copy
import unittest

from bsa.engine import ProjectError
from bsa.revit_connectivity import diagnose


class RevitConnectivityTests(unittest.TestCase):
    def setUp(self):
        def connector(target):
            return dict(id=1, origin_m=[1, 0, 0], domain='DomainPiping', connector_type='End',
                        physically_connected=True, references=[dict(owner_unique_id=target, connector_id=1,
                        connector_type='End', domain='DomainPiping', origin_m=[1, 0, 0],
                        api_connected_to=True, reciprocal_reference=True, separation_m=0)])
        self.data = dict(units='metres', pipes=[dict(unique_id='pipe', connectors=[connector('fitting')])],
                         fittings=[dict(unique_id='fitting', connectors=[connector('pipe')])])

    def check_reason(self, reason):
        result = diagnose(self.data, 0.0001)
        self.assertEqual(result['diagnostic_status'], 'fail')
        self.assertTrue(any(reason in row['reasons'] for row in result['issues']))

    def test_consistent_pairs_never_certify_system(self):
        result = diagnose(self.data, 0.0001)
        self.assertEqual(len(result['consistent_reference_pairs']), 1)
        self.assertEqual(result['diagnostic_status'], 'pending')
        self.assertFalse(result['connected_system_verified'])

    def test_fake_reciprocity_detected_from_opposite_inventory(self):
        self.data['fittings'][0]['connectors'][0]['references'] = []
        self.check_reason('missing_reciprocal_reference')

    def test_one_sided_metadata_failure_cannot_leave_a_consistent_pair(self):
        for field, value in (('reciprocal_reference', False), ('origin_m', [1.02, 0, 0]),
                             ('separation_m', 0.02), ('connector_type', 'Logical')):
            data = copy.deepcopy(self.data)
            data['fittings'][0]['connectors'][0]['references'][0][field] = value
            with self.subTest(field=field):
                result = diagnose(data, 0.0001)
                self.assertEqual(result['diagnostic_status'], 'fail')
                self.assertEqual(result['consistent_reference_pairs'], [])

    def test_moved_target_with_unchanged_claims(self):
        self.data['fittings'][0]['connectors'][0]['origin_m'] = [1.02, 0, 0]
        self.check_reason('endpoint_separation')
        self.check_reason('reference_position_mismatch')
        self.check_reason('recorded_separation_mismatch')

    def test_logical_reference_does_not_count_as_physical(self):
        c = self.data['pipes'][0]['connectors'][0]
        c['references'][0]['connector_type'] = 'Logical'
        self.check_reason('physical_flag_without_physical_reference')

    def test_uncovered_equipment_is_pending(self):
        self.data['pipes'][0]['connectors'][0]['references'][0]['owner_unique_id'] = 'pump'
        self.data['fittings'] = []
        result = diagnose(self.data, 0.0001)
        self.assertEqual(result['pending'][0]['reason'], 'target_outside_inventory')
        self.assertEqual(result['diagnostic_status'], 'pending')

    def test_open_port_not_automatically_an_error_or_approved_terminal(self):
        c = self.data['pipes'][0]['connectors'][0]
        c.update(physically_connected=False, references=[])
        self.data['fittings'] = []
        result = diagnose(self.data, 0.0001)
        self.assertEqual(result['observed_open_ports'], [('pipe', 1)])
        self.assertEqual(result['diagnostic_status'], 'pending')

    def test_domain_and_api_disagreement(self):
        c = self.data['fittings'][0]['connectors'][0]
        c['domain'] = 'DomainHvac'
        c['references'][0]['api_connected_to'] = False
        self.check_reason('domain_mismatch')
        self.check_reason('api_relation_not_confirmed')

    def test_invalid_evidence_rejected(self):
        for mutation in ('duplicate', 'nan', 'units', 'missing_flag'):
            data = copy.deepcopy(self.data)
            c = data['pipes'][0]['connectors'][0]
            if mutation == 'duplicate': data['pipes'].append(copy.deepcopy(data['pipes'][0]))
            if mutation == 'nan': c['origin_m'][0] = float('nan')
            if mutation == 'units': data['units'] = 'feet'
            if mutation == 'missing_flag': del c['physically_connected']
            with self.subTest(mutation=mutation), self.assertRaises(ProjectError):
                diagnose(data, 0.0001)


if __name__ == '__main__': unittest.main()
