import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.regulations import evaluate

ROOT = Path(__file__).resolve().parents[1]


class PlumbingPumpRulesTests(unittest.TestCase):
    def test_boundaries_missing_data_and_source_integrity(self):
        pack = json.loads((ROOT/'regulations/hk/plumbing-pumps-2026.11.09/pack.json').read_text())
        project = json.loads((ROOT/'examples/hk-plumbing-pumps/facts.json').read_text())
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); pdf = root/'wsd-tr-2026-04.pdf'
            pdf.write_bytes(b'SYNTHETIC UNIT TEST SOURCE, NOT OFFICIAL EVIDENCE')
            pack['sources']['wsd_tr_2026_04']['sha256'] = digest(pdf)
            def check(data):return evaluate(pack, data, root)
            result = check(project)
            self.assertTrue(result['supported_checks_pass'])
            self.assertFalse(result['design_accepted'])
            self.assertEqual(result['regulatory_compliance'], 'not_established')
            self.assertEqual(result['checks'][0]['binding_status'], 'sourced_assertions_only')
            for value, expected in ((.0025, 'pass'), (.00249, 'review_required')):
                data = copy.deepcopy(project); data['sump_pump']['available_pumping_capacity']['value'] = value
                self.assertEqual(check(data)['checks'][0]['status'], expected)
            data = copy.deepcopy(project); data['sump_pump']['duplicate_pumpset_provided']['value'] = False
            self.assertEqual(check(data)['checks'][0]['status'], 'review_required')
            for key in project['sump_pump']:
                data = copy.deepcopy(project); del data['sump_pump'][key]
                self.assertEqual(check(data)['checks'][0]['status'], 'pending', key)
            for value in (0, -1, True, float('nan'), float('inf')):
                data = copy.deepcopy(project); data['sump_pump']['available_pumping_capacity']['value'] = value
                self.assertEqual(check(data)['checks'][0]['status'], 'pending')
            data = copy.deepcopy(project); data['sump_pump']['available_pumping_capacity']['unit'] = 'L/s'
            self.assertEqual(check(data)['checks'][0]['status'], 'pending')
            data = copy.deepcopy(project); data['edition_decisions'] = {}
            self.assertEqual(check(data)['checks'][0]['status'], 'pending')
            data = copy.deepcopy(project); data['facts']['sump_and_pump_system']['value'] = False
            self.assertEqual(check(data)['checks'][0]['status'], 'not_applicable')
            self.assertFalse(check(data)['supported_checks_pass'])
            pdf.write_bytes(b'changed')
            self.assertEqual(check(project)['checks'][0]['status'], 'pending')
