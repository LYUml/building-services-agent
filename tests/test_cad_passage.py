import copy
import math
import unittest
from bsa.cad_passage import validate, check_probe
from bsa.engine import ProjectError


class PassageTests(unittest.TestCase):
    def probe(self):
        return {'id': 'p', 'source': 'Synthetic oblique cylinder', 'role': 'passage',
                'start': [0, 0, 0], 'end': [3, 4, 0], 'radius': 1}

    def report(self):
        return 'Volume: 15.70796327\nBounding box: X: -0.80000000 -- 3.80000000\nY: -0.60000000 -- 4.60000000\nZ: -1.00000000 -- 1.00000000\n'

    def test_oblique_native_probe_independent_reference(self):
        r = check_probe(self.report(), self.probe())
        self.assertAlmostEqual(r['volume_drawing_units3'], 5*math.pi, places=7)

    def test_wrong_volume_bounds_and_missing_or_duplicate_evidence_reject(self):
        for report in (self.report().replace('15.70796327', '0'),
                       self.report().replace('3.80000000', '3.00000000'),
                       '', self.report() + self.report()):
            with self.assertRaises(ProjectError): check_probe(report, self.probe())
        tiny = dict(self.probe(), radius=1e-6)
        with self.assertRaises(ProjectError): check_probe(self.report(), tiny)

    def test_controls_identity_and_finite_geometry_required(self):
        p = self.probe(); wall = dict(p, id='w', role='wall_control')
        b = {'source': 'Synthetic control', 'drawing_sha256': 'a'*64, 'solid_handle': '94',
             'insunits': 1, 'probes': [p, wall]}
        validate(b)
        for update in ({'probes': [p]}, {'probes': [wall]}, {'probes': [p, p, wall]},
                       {'insunits': True}, {'drawing_sha256': 'unknown'}):
            with self.assertRaises(ProjectError): validate(dict(b, **update))
        for key, value in [('radius', float('nan')), ('end', [0, 0, 0]), ('id', '../outside')]:
            bad = copy.deepcopy(b); bad['probes'][0][key] = value
            with self.assertRaises(ProjectError): validate(bad)
