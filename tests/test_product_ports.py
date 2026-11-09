import copy
import unittest
import ezdxf
import numpy as np
from bsa.product_ports import anchors, frame
from bsa.engine import ProjectError


class ProductPortTests(unittest.TestCase):
    def fixture(self):
        doc = ezdxf.new(); doc.units = 1
        main = doc.modelspace().add_line((-2.75, 0, 0), (2.75, 0, 0))
        branch = doc.modelspace().add_line((0, 0, 0), (0, 0, -2.75))
        ports = [{'id': name, 'source': 'Synthetic CAD centreline', 'line_handle': handle,
                  'endpoint': end, 'passage_id': probe} for name, handle, end, probe in
                 [('a', main.dxf.handle, 'start', 'm'), ('b', main.dxf.handle, 'end', 'm'),
                  ('c', branch.dxf.handle, 'end', 'b')]]
        probes = [{'id': 'm', 'role': 'passage', 'start': [-2.8, 0, 0], 'end': [2.8, 0, 0]},
                  {'id': 'b', 'role': 'passage', 'start': [0, 0, -2.8], 'end': [0, 0, 0]}]
        return doc, ports, probes

    def test_source_endpoint_units_and_outward_axis(self):
        doc, ports, probes = self.fixture(); result = anchors(doc, ports, probes, .0254)
        self.assertTrue(np.allclose(result['a'][:3, 3], [-.06985, 0, 0]))
        self.assertTrue(np.array_equal(result['a'][:3, 2], [-1, 0, 0]))
        self.assertTrue(np.array_equal(result['c'][:3, 2], [0, 0, -1]))
        for mat in result.values():
            self.assertAlmostEqual(np.linalg.det(mat[:3, :3]), 1)
            self.assertTrue(np.allclose(mat[:3, :3].T@mat[:3, :3], np.eye(3)))

    def test_wrong_handle_duplicate_and_uncovered_anchor_reject(self):
        doc, ports, probes = self.fixture()
        for key, value in [('line_handle', 'FFFF'), ('passage_id', 'missing'), ('endpoint', 'middle')]:
            bad = copy.deepcopy(ports); bad[0][key] = value
            with self.assertRaises(ProjectError): anchors(doc, bad, probes, .0254)
        bad = copy.deepcopy(ports); bad[1]['endpoint'] = 'start'
        with self.assertRaises(ProjectError): anchors(doc, bad, probes, .0254)
        probes[0]['start'][0] = -2
        with self.assertRaises(ProjectError): anchors(doc, ports, probes, .0254)

    def test_oblique_frame(self):
        m = frame([1, 2, 3], [1, 2, 3])
        self.assertTrue(np.allclose(m[:3, 2], np.array([1, 2, 3])/np.sqrt(14)))
        self.assertTrue(np.allclose(m[:3, :3].T@m[:3, :3], np.eye(3)))
