import unittest

from bsa.ifc_port_inventory import compare, compare_positions, inspect_pair_gaps


class IfcPortComparisonTests(unittest.TestCase):
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
        self.assertEqual(inspect_pair_gaps(inventory, 0.02)['separated_relationships'], [])

    def test_position_tolerance_and_missing_placements(self):
        previous = {'ports': [dict(guid='a', origin_m=[0, 0, 0]), dict(guid='b', origin_m=None)]}
        current = {'ports': [dict(guid='a', origin_m=[0.02, 0, 0]), dict(guid='b', origin_m=[0, 0, 0])]}
        checked = compare_positions(previous, current, 0.001)
        self.assertEqual(checked['comparable_ports'], 1)
        self.assertEqual(checked['unavailable_ports'], ['b'])
        self.assertEqual(checked['moved_ports'][0]['displacement_m'], 0.02)
        self.assertEqual(compare_positions(previous, current, 0.03)['moved_ports'], [])

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
        self.assertEqual(result['changed_pairs'], [dict(port_guids=('a', 'b'), before=1, after=0)])
        self.assertEqual(compare(old, dict(ports=[], connections=[]))['status'], 'no_shared_port_guids')
