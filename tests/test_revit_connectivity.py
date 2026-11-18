"""Synthetic fault injection only; does not substitute for running Revit."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bsa.engine import ProjectError
from bsa.revit_connectivity import diagnose, run
from bsa.source_refs import file_hash


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

    def test_automation_inventory_binds_remote_copy_to_local_preparation(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            root = Path(temporary)
            model, inventory = root / 'fixture.rvt', root / 'inventory.json'
            receipt, out = root / 'preparation.json', root / 'diagnosis.json'
            model.write_bytes(b'synthetic fixture bytes')
            pins = dict(saved_rvt_sha256=file_hash(model), request_sha256='a'*64, assembly_sha256='b'*64)
            receipt.write_text(json.dumps(pins), encoding='utf-8')
            captured = dict(self.data, document_path='X:/work/input.rvt', adapter_sha256=pins['assembly_sha256'],
                            request_sha256=pins['request_sha256'], saved_rvt_sha256=pins['saved_rvt_sha256'])
            inventory.write_text(json.dumps(captured), encoding='utf-8')
            result = run(inventory, model, out, 0.001, automation_receipt=receipt)
            self.assertEqual(result['automation_receipt_sha256'], file_hash(receipt))
            self.assertEqual(result['diagnostic_status'], 'pending')
            rejected = root / 'rejected.json'
            with self.assertRaisesRegex(ProjectError, 'selected saved model'):
                run(inventory, model, rejected, 0.001)
            for field in ('adapter_sha256', 'request_sha256', 'saved_rvt_sha256'):
                with self.subTest(field=field):
                    inventory.write_text(json.dumps(dict(captured, **{field: 'c'*64})), encoding='utf-8')
                    with self.assertRaises(ProjectError):
                        run(inventory, model, rejected, 0.001, automation_receipt=receipt)
                    self.assertFalse(rejected.exists())

    def test_consistent_pairs_never_certify_system(self):
        result = diagnose(self.data, 0.0001)
        self.assertEqual(len(result['consistent_reference_pairs']), 1)
        self.assertEqual(result['diagnostic_status'], 'pending')
        self.assertFalse(result['connected_system_verified'])

    def test_expected_pairs_detect_coincident_wrong_peers_and_missing_link(self):
        intent = dict(source='Synthetic design schedule, rows 1–2', required_pairs=[
            [['pipe', 1], ['fitting', 1]], [['pipe-2', 1], ['fitting-2', 1]],
        ])
        for kind in ('pipes', 'fittings'):
            second = copy.deepcopy(self.data[kind][0])
            second['unique_id'] += '-2'
            second['connectors'][0]['references'][0]['owner_unique_id'] += '-2'
            self.data[kind].append(second)
        matched = diagnose(self.data, 0.0001, expected_connections=intent)
        self.assertEqual(matched['expected_connections']['status'], 'pass')
        self.assertEqual(matched['diagnostic_status'], 'pending')
        for kind in ('pipes', 'fittings'):
            first, second = self.data[kind]
            a, b = first['connectors'][0], second['connectors'][0]
            a['references'], b['references'] = b['references'], a['references']
        swapped = diagnose(self.data, 0.0001, expected_connections=intent)
        self.assertEqual(len(swapped['consistent_reference_pairs']), 2)
        self.assertEqual(swapped['diagnostic_status'], 'fail')
        self.assertEqual(len(swapped['expected_connections']['missing_pairs']), 2)
        self.assertEqual(len(swapped['expected_connections']['unexpected_pairs']), 2)
        for kind in ('pipes', 'fittings'):
            for item in self.data[kind]:
                item['connectors'][0].update(references=[], physically_connected=False)
        disconnected = diagnose(self.data, 0.0001, expected_connections=intent)
        self.assertEqual(len(disconnected['expected_connections']['missing_pairs']), 2)
        self.assertEqual(disconnected['expected_connections']['unexpected_pairs'], [])

    def test_connected_pair_moved_together_fails_declared_position(self):
        for item in (self.data['pipes'][0], self.data['fittings'][0]):
            connector = item['connectors'][0]
            connector['origin_m'] = [1.02, 0, 0]
            connector['references'][0]['origin_m'] = [1.02, 0, 0]
        intent = dict(source='Synthetic coordinate schedule row 1',
                      required_pairs=[[['pipe', 1], ['fitting', 1]]],
                      port_positions_m=[dict(port=['pipe', 1], origin_m=[1, 0, 0])])
        result = diagnose(self.data, 0.001, expected_connections=intent)
        self.assertEqual(len(result['expected_connections']['matched_pairs']), 1)
        self.assertEqual(result['diagnostic_status'], 'fail')
        check, = result['expected_connections']['port_position_checks']
        self.assertEqual(check['observed_origin_m'], [1.02, 0, 0])
        self.assertAlmostEqual(check['displacement_m'], 0.02)
        self.assertEqual(check['status'], 'fail')

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
