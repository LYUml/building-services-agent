import unittest

from bsa.openfoam_mesh_review import assess_check_mesh


class MeshReviewTests(unittest.TestCase):
    def test_native_failure_with_zero_exit(self):
        r = assess_check_mesh('Failed 3 mesh checks.\n\nEnd\n', 0)
        self.assertEqual(r['reported_failed_checks'], [3])
        self.assertFalse(r['native_mesh_checks_passed'])

    def test_complete_success_never_accepts_engineering(self):
        r = assess_check_mesh('Mesh OK.\n\nEnd\n', 0)
        self.assertTrue(r['native_mesh_checks_passed'])
        self.assertFalse(r['engineering_accepted'])

    def test_incomplete_conflicting_or_crashed_logs_fail_closed(self):
        for log, code in [('Mesh OK.\n', 0), ('End\n', 0),
                          ('Mesh OK.\nEnd\n', 3),
                          ('Mesh OK.\nFailed 1 mesh checks.\nEnd\n', 0),
                          ('Mesh OK.\nBacktrace:\nEnd\n', 0),
                          ('Mesh OK.\nMesh OK.\nEnd\n', 0)]:
            with self.subTest(log=log, code=code):
                self.assertFalse(assess_check_mesh(log, code)['native_mesh_checks_passed'])


if __name__ == '__main__':
    unittest.main()
