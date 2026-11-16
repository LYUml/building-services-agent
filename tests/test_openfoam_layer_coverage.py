import unittest

from bsa.openfoam_mesh_review import assess_check_mesh, assess_layer_coverage


class LayerCoverageTests(unittest.TestCase):
    def test_mesh_ok_does_not_clear_actual_zero_layers(self):
        self.assertTrue(assess_check_mesh('Mesh OK.\nEnd\n', 0)['native_mesh_checks_passed'])
        result = assess_layer_coverage({'wall': {'face_count': 15438, 'values': 0}}, 18)
        self.assertEqual(result['any_layer_face_fraction'], 0)
        self.assertFalse(result['all_wall_faces_have_requested_layers'])

    def test_mean_requested_count_cannot_hide_an_unlayered_face(self):
        result = assess_layer_coverage({'wall': {'face_count': 2, 'values': [0, 36]}}, 18)
        self.assertEqual(result['requested_layer_face_fraction'], .5)
        self.assertFalse(result['all_wall_faces_have_requested_layers'])

    def test_complete_face_counts_do_not_accept_area_height_or_flow(self):
        result = assess_layer_coverage({'a': {'face_count': 2, 'values': [18, 18]},
                                       'b': {'face_count': 3, 'values': 18}}, 18)
        self.assertTrue(result['all_wall_faces_have_requested_layers'])
        self.assertEqual(result['wall_faces'], 5)
        for key in ['wall_area_coverage_verified', 'actual_first_layer_height_verified',
                    'yPlus_verified', 'engineering_accepted']:
            self.assertFalse(result[key])

    def test_native_count_and_type_corruption_rejected(self):
        for values in [[18], [True, 18], [-1, 18], [1.5, 18], [float('nan'), 18], True]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                assess_layer_coverage({'wall': {'face_count': 2, 'values': values}}, 18)

    def test_missing_wall_scope_and_boolean_targets_rejected(self):
        for patches, target in [({}, 18), ({'wall': {'face_count': True, 'values': 18}}, 18),
                                ({'wall': {'face_count': 2, 'values': 18}}, True)]:
            with self.subTest(patches=patches, target=target), self.assertRaises(ValueError):
                assess_layer_coverage(patches, target)


if __name__ == '__main__':
    unittest.main()
