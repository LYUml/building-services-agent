import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bsa.cfd_mesh_boundary import check


OUTER = [(0,1,3), (0,3,2), (1,2,3), (0,4,1), (0,2,4), (1,4,2)]
INTERNAL = (0,1,2)


def fixture(outer=None, internal_marker='wall', duplicate_cell=False):
    outer = OUTER if outer is None else outer
    rows = ['NDIME=3', 'NELEM='+('3' if duplicate_cell else '2'),
            '10 0 1 2 3 0', '10 0 2 1 4 1']
    if duplicate_cell:
        rows.append('10 0 1 2 3 2')
    rows += ['NPOIN=5', '0 0 0 0', '1 0 0 1', '0 1 0 2', '0 0 1 3', '0 0 -1 4']
    groups = {'wall': list(outer)}
    groups.setdefault(internal_marker, []).append(INTERNAL)
    rows.append('NMARK='+str(len(groups)))
    for name, faces in groups.items():
        rows += ['MARKER_TAG='+name, 'MARKER_ELEMS='+str(len(faces))]
        rows += ['5 '+' '.join(map(str, face)) for face in faces]
    return ('\r\n'.join(rows)+'\r\n').encode()


class MeshBoundaryTests(unittest.TestCase):
    def test_only_internal_wall_removed_and_prefix_preserved(self):
        source = fixture()
        result, report = check(source, remove_internal_walls=True)
        prefix = source[:source.index(b'MARKER_TAG=')]
        self.assertTrue(result.startswith(prefix))
        self.assertEqual(report['removed_internal_wall_faces'], {'wall': 1})
        self.assertEqual(report['exterior_faces'], 6)
        self.assertFalse(report['engineering_accepted'])
        unchanged, second = check(result)
        self.assertEqual(result, unchanged)
        self.assertEqual(second['removed_internal_wall_faces'], {})

    def test_repair_requires_opt_in_and_never_drops_flow_marker(self):
        with self.assertRaisesRegex(ValueError, 'explicit wall-marker'):
            check(fixture())
        with self.assertRaisesRegex(ValueError, 'explicit wall-marker'):
            check(fixture(internal_marker='inlet'), remove_internal_walls=True)

    def test_invalid_exterior_and_nonmanifold_sources_rejected(self):
        flipped = list(OUTER)
        flipped[0] = tuple(reversed(flipped[0]))
        nonmanifold = fixture(duplicate_cell=True).replace(b'10 0 1 2 3 2', b'10 0 1 2 5 2')
        nonmanifold = nonmanifold.replace(b'NPOIN=5', b'NPOIN=6').replace(b'NMARK=1', b'0 0 2 5\r\nNMARK=1')
        cases = [fixture(OUTER[:-1]), fixture(OUTER+[OUTER[0]]),
                 fixture(OUTER+[(0,3,4)]), fixture(flipped),
                 fixture(duplicate_cell=True), nonmanifold,
                 fixture().replace(b'0 0 0 0\r\n', b'nan 0 0 0\r\n')]
        for source in cases:
            with self.subTest(source=source), self.assertRaises(ValueError):
                check(source, remove_internal_walls=True)

    def test_cli_host_paths_and_existing_outputs_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = fixture()
            (root/'source.su2').write_bytes(source)
            env = dict(os.environ, BSA_PROJECT_ROOT=str(root))
            command = [sys.executable, '-m', 'bsa.cfd_mesh_boundary', '--mesh', 'source.su2',
                       '--report', 'review.json', '--output-mesh', 'repaired.su2', '--remove-internal-walls']
            first = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            output = (root/'repaired.su2').read_bytes()
            self.assertEqual((root/'source.su2').read_bytes(), source)
            again = subprocess.run(command, env=env, capture_output=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual((root/'repaired.su2').read_bytes(), output)
            outside = root.parent/(root.name+'-outside.json')
            escape = [sys.executable, '-m', 'bsa.cfd_mesh_boundary', '--mesh', 'source.su2',
                      '--report', str(outside)]
            rejected = subprocess.run(escape, env=env, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(outside.exists())


if __name__ == '__main__':
    unittest.main()
