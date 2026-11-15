import unittest
from bsa.cfd_native_probe import extract


MESH = b'NDIME=3\nNPOIN=3\n0 0 0 0\n1 0 0 1\n0 1 0 2\n'
FIELD = b'"PointID","x","y","z","Velocity_x"\n2,0,1,0,9\n1,1,0,0,4\n0,0,0,0,2\n'


class NativeProbeTests(unittest.TestCase):
    def run_probe(self, data=FIELD, **kwargs):
        return extract(MESH, data, [0, 0, 0], [1, 0, 0], ['Velocity_x'], **kwargs)

    def test_identifiers_bind_shuffled_rows_without_interpolation(self):
        result = self.run_probe()
        self.assertEqual([r['point_id'] for r in result['nodes']], [0, 1])
        self.assertEqual([r['values']['Velocity_x'] for r in result['nodes']], [2, 4])
        self.assertFalse(result['engineering_accepted'])

    def test_other_mesh_with_same_number_of_points_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, 'coordinates'):
            self.run_probe(FIELD.replace(b'1,1,0,0,4', b'1,1,0.001,0,4'))

    def test_duplicate_partial_foreign_and_nonfinite_fields_rejected(self):
        cases = [FIELD.rsplit(b'0,0,0,0,2', 1)[0],
                 FIELD.replace(b'0,0,0,0,2', b'1,1,0,0,2'),
                 FIELD.replace(b'0,0,0,0,2', b'3,0,0,0,2'),
                 FIELD.replace(b'0,0,0,0,2', b'0,0,0,0,nan')]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.run_probe(case)

    def test_no_nodes_off_line_and_invalid_geometry_rejected(self):
        with self.assertRaises(ValueError):
            extract(MESH, FIELD, [0, 0, 1], [1, 0, 1], ['Velocity_x'])
        for tolerance in [True, 0, float('nan')]:
            with self.assertRaises(ValueError):
                self.run_probe(tolerance=tolerance)


if __name__ == '__main__':
    unittest.main()
