import unittest

from bsa.cfd_node_order import gmsh_to_su2, su2_to_gmsh


class NodeOrderTests(unittest.TestCase):
    def test_pinned_prism_order_and_roundtrip_without_id_base_change(self):
        source = [10, 20, 30, 40, 50, 60]
        kind, nodes = su2_to_gmsh(13, source)
        self.assertEqual((kind, nodes), (6, (10, 30, 20, 40, 60, 50)))
        self.assertEqual(gmsh_to_su2(kind, nodes), (13, tuple(source)))
        self.assertEqual(source, [10, 20, 30, 40, 50, 60])
        self.assertEqual(su2_to_gmsh(10, [0, 1, 2, 3]), (4, (0, 1, 2, 3)))
        self.assertEqual(gmsh_to_su2(4, [0, 1, 2, 3]), (10, (0, 1, 2, 3)))

    def test_prism_reference_handedness_requires_permutation(self):
        # SU2/VTK wedge order has the opposite base orientation to Gmsh.
        xyz = [(0, 0, 0), (0, 1, 0), (1, 0, 0),
               (0, 0, 1), (0, 1, 1), (1, 0, 1)]

        def triple(nodes):
            a, b, c, d = (xyz[nodes[i]] for i in (0, 1, 2, 3))
            u = [b[i]-a[i] for i in range(3)]
            v = [c[i]-a[i] for i in range(3)]
            w = [d[i]-a[i] for i in range(3)]
            return (u[0]*(v[1]*w[2]-v[2]*w[1])
                    - u[1]*(v[0]*w[2]-v[2]*w[0])
                    + u[2]*(v[0]*w[1]-v[1]*w[0]))

        self.assertLess(triple(range(6)), 0)
        self.assertGreater(triple(su2_to_gmsh(13, range(6))[1]), 0)

    def test_unsupported_or_malformed_connectivity_rejected(self):
        for convert in (su2_to_gmsh, gmsh_to_su2):
            for kind in (True, '13', 12, 99):
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    convert(kind, range(6))
        for nodes in ([0, 1, 2], [0, 1, 1, 3], [0, True, 2, 3],
                      [0, 1.0, 2, 3], [0, -1, 2, 3], None):
            with self.subTest(nodes=nodes), self.assertRaises(ValueError):
                su2_to_gmsh(10, nodes)


if __name__ == '__main__':
    unittest.main()
