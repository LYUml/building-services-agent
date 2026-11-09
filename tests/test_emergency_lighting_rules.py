import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bsa.regulations import evaluate


ROOT = Path(__file__).resolve().parents[1]


class EmergencyRulesTests(unittest.TestCase):
    def setUp(self):
        self.pack = json.loads((ROOT / 'regulations/hk/emergency-accommodation-2026.11.09/pack.json').read_text())
        self.project = json.loads((ROOT / 'examples/regulations-hk/emergency-accommodation.json').read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.pack['sources']['fsd_guidance_2021']
        (self.root / source['cache_filename']).write_bytes(b'test-only source')
        source['sha256'] = hashlib.sha256(b'test-only source').hexdigest()

    def result(self):
        return evaluate(self.pack, self.project, self.root)

    def test_threshold_boundaries(self):
        data = self.project['emergency_accommodation']
        for area, ids, lux, expected in [
            (8, ['A'], 2, 'pass'), (8.000001, ['A'], 2, 'review_required'),
            (9, ['A', 'B'], 1.9999, 'review_required'),
            (9, ['A', 'B'], 2, 'pass')]:
            with self.subTest(area=area, lux=lux):
                data['gross_area']['value'] = area
                data['minimum_illuminance']['value'] = lux
                data['emergency_luminaire_ids']['value'] = ids
                r = self.result()
                self.assertEqual(r['checks'][0]['status'], expected)
                self.assertFalse(r['design_accepted'])

    def test_normal_mode_and_incomplete_assessment_cannot_pass(self):
        original = copy.deepcopy(self.project)
        for key in ('emergency_mode', 'floor_horizontal_assessment',
                    'whole_area_minimum_assessed', 'entire_rated_duration_assessed'):
            self.project = copy.deepcopy(original)
            self.project['emergency_accommodation'][key]['value'] = False
            self.assertEqual(self.result()['checks'][0]['status'], 'pending')

    def test_invalid_inputs_and_duplicate_ids(self):
        original = copy.deepcopy(self.project)
        for key, value in [('gross_area', True), ('minimum_illuminance', float('nan')),
                           ('emergency_luminaire_ids', ['A', 'A']),
                           ('emergency_luminaire_ids', [{'id': 'A'}])]:
            self.project = copy.deepcopy(original)
            self.project['emergency_accommodation'][key]['value'] = value
            self.assertEqual(self.result()['checks'][0]['status'], 'pending')

    def test_source_and_edition_gates(self):
        self.project['edition_decisions'] = {}
        self.assertEqual(self.result()['checks'][0]['status'], 'pending')
        source = self.pack['sources']['fsd_guidance_2021']
        (self.root / source['cache_filename']).write_bytes(b'changed')
        self.assertIn('pinned official source unavailable or changed',
                      self.result()['checks'][0]['reasons'])

    def test_excluded_path_is_not_compliance(self):
        self.project['facts']['outside_licensed_premises_specific_path']['value'] = False
        r = self.result()
        self.assertEqual(r['checks'][0]['status'], 'not_applicable')
        self.assertFalse(r['supported_checks_pass'])


if __name__ == '__main__':
    unittest.main()
