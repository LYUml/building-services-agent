import unittest

from bsa.ifc_port_inventory import compare


class IfcPortComparisonTests(unittest.TestCase):
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
