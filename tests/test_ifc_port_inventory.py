import unittest

from bsa.ifc_port_inventory import compare, compare_positions, gap_status, inspect_pair_gaps, review_status
from bsa.ifc_port_bcf import issue_records


class IfcPortComparisonTests(unittest.TestCase):
    def test_bcf_baseline_findings_use_only_current_view_coordinates(self):
        report = dict(source_sha256='current', ports=[dict(guid='a', owner_guids=['product'], origin_m=[100.02, 0, 0])],
                      connection_gaps={'separated_relationships': [], 'unavailable_relationships': []},
                      connection_ownership={'conflicting_ports': []},
                      comparison=dict(status='shared_port_guids', baseline_sha256='previous', max_port_shift_m=0.005,
                          changed_pairs=[dict(port_guids=['a', 'b'], before=1, after=0)],
                          positions={'moved_ports': [dict(guid='a', before_m=[0, 0, 0],
                              after_m=[100.02, 0, 0], aligned_after_m=[0.02, 0, 0], displacement_m=0.02)]}))
        pair, movement = issue_records(report)
        self.assertIn('1 baseline relation(s), 0 current relation(s)', pair[1])
        self.assertIn('Aligned current origin: [0.02, 0, 0]', movement[1])
        for issue in (pair, movement):
            self.assertEqual(issue[2:], (['product'], [100.02, 0, 0]))

    def test_pair_gap_and_unavailable_coordinates_remain_distinct(self):
        inventory = dict(ports=[dict(guid='a', origin_m=[0, 0, 0]),
                                dict(guid='b', origin_m=[0.02, 0, 0]),
                                dict(guid='c', origin_m=None)],
                         connections=[dict(guid='gap', port_guids=['a', 'b']),
                                      dict(guid='unknown', port_guids=['b', 'c'])])
        checked = inspect_pair_gaps(inventory, 0.001)
        self.assertEqual(checked['measured_relationships'], 1)
        self.assertEqual(checked['unavailable_relationships'], ['unknown'])
        self.assertEqual(checked['separated_relationships'][0]['separation_m'], 0.02)
        self.assertEqual(gap_status(checked)[0], 'fail')
        self.assertEqual(gap_status(inspect_pair_gaps(inventory, 0.02))[0], 'pending')
        inventory['connections'].pop()
        self.assertEqual(gap_status(inspect_pair_gaps(inventory, 0.02))[0], 'pass')
        report = dict(connection_gaps=inspect_pair_gaps(inventory, 0.02))
        report['connection_ownership'] = dict(conflicting_ports=['a'], unavailable_ports=[])
        self.assertEqual(review_status(report)[0], 'fail')
        report['connection_ownership'] = dict(conflicting_ports=[], unavailable_ports=['a'])
        self.assertEqual(review_status(report)[0], 'pending')
        inventory['connections'].clear()
        self.assertEqual(gap_status(inspect_pair_gaps(inventory, 0.02))[0], 'pending')

    def test_position_tolerance_and_missing_placements(self):
        previous = {'ports': [dict(guid='a', origin_m=[0, 0, 0]), dict(guid='b', origin_m=None)]}
        current = {'ports': [dict(guid='a', origin_m=[0.02, 0, 0]), dict(guid='b', origin_m=[0, 0, 0])]}
        checked = compare_positions(previous, current, 0.001)
        self.assertEqual(checked['comparable_ports'], 1)
        self.assertEqual(checked['unavailable_ports'], ['b'])
        self.assertEqual(checked['moved_ports'][0]['displacement_m'], 0.02)
        self.assertEqual(compare_positions(previous, current, 0.03)['moved_ports'], [])
        scope = dict(measured_relationships=1, separated_relationships=[], unavailable_relationships=[], scope='test')
        comparison = dict(status='shared_port_guids', added_ports=[], removed_ports=[], changed_ports=[],
                          changed_pairs=[], positions=checked)
        report = dict(connection_gaps=scope, comparison=comparison)
        self.assertEqual(review_status(report)[0], 'pass')
        comparison['max_port_shift_m'] = 0.001
        self.assertEqual(review_status(report)[0], 'fail')
        comparison['positions'] = compare_positions(previous, current, 0.03)
        self.assertEqual(review_status(report)[0], 'pending')

    def test_alignment_preserves_raw_and_adjusted_coordinates(self):
        before = {'ports': [dict(guid='p', origin_m=[0, 0, 0])]}
        after = {'ports': [dict(guid='p', origin_m=[100.02, 0, 0])]}
        checked = compare_positions(before, after, 0.005,
                                    alignment={'current_to_baseline_m': [-100, 0, 0]})
        moved, = checked['moved_ports']
        self.assertEqual(moved['after_m'], [100.02, 0, 0])
        self.assertAlmostEqual(moved['aligned_after_m'][0], 0.02)
        self.assertAlmostEqual(moved['displacement_m'], 0.02)

    def test_alignment_rotates_before_translating(self):
        before = {'ports': [dict(guid='p', origin_m=[1, 2, 3])]}
        after = {'ports': [dict(guid='p', origin_m=[98, 21.02, 3])]}
        result = compare_positions(before, after, 0.005, alignment=dict(
            current_to_baseline_yaw_deg=-90, current_to_baseline_m=[-20, 100, 0]))
        moved, = result['moved_ports']
        self.assertAlmostEqual(moved['aligned_after_m'][0], 1.02)
        self.assertAlmostEqual(moved['aligned_after_m'][1], 2)
        self.assertAlmostEqual(moved['displacement_m'], 0.02)

    def test_pair_removal_owner_change_and_empty_export(self):
        a = dict(guid='a', owner_guids=['p1'], flow_direction='SOURCE')
        b = dict(guid='b', owner_guids=['p2'], flow_direction='SINK')
        pair = dict(guid='r1', port_guids=['a', 'b'])
        old = dict(ports=[a, b], connections=[pair], source_sha256='old', schema='IFC2X3')

        revised = dict(ports=[{**a, 'owner_guids': ['p3']}, b],
                       connections=[dict(guid='r2', port_guids=['b', 'a'])])
        result = compare(old, revised)
        self.assertEqual(result['shared_ports'], 2)
        self.assertEqual(result['changed_pairs'], [])
        self.assertEqual(result['changed_ports'][0]['guid'], 'a')
        revised['connections'] = []
        result = compare(old, revised)
        self.assertEqual(result['changed_pairs'], [dict(port_guids=['a', 'b'], before=1, after=0)])
        gaps = dict(measured_relationships=1, separated_relationships=[], unavailable_relationships=[], scope='test')
        self.assertEqual(review_status(dict(connection_gaps=gaps, comparison=result))[0], 'fail')
        no_overlap = compare(old, dict(ports=[], connections=[]))
        self.assertEqual(no_overlap['status'], 'no_shared_port_guids')
        self.assertEqual(review_status(dict(connection_gaps=gaps, comparison=no_overlap))[0], 'pending')
