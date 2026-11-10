import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from bsa.terminal_throw import evaluate, run


class TerminalThrowTests(unittest.TestCase):
    def run_case(self, **kw):
        args=dict(rows=[{'flow_L_s':20,'T025_m':1},{'flow_L_s':100,'T025_m':5}],
                  maximum_flow_L_s=100,turndown=.4,characteristic_length_m=2)
        args.update(kw)
        return evaluate(**args)

    def test_endpoint_and_interpolation(self):
        r=self.run_case()
        self.assertEqual(r['cases']['maximum']['T025_m'],5)
        self.assertEqual(r['cases']['minimum']['T025_m'],2)
        self.assertEqual(r['cases']['minimum']['ratio'],1)
        self.assertFalse(r['ADPI_verified'])

    def test_outside_not_clamped(self):
        r=self.run_case(maximum_flow_L_s=110,turndown=.1)
        for c in r['cases'].values():
            self.assertEqual(c['status'],'outside_catalogue')
            self.assertIsNone(c['ratio'])

    def test_invalid(self):
        for kw in [dict(turndown=True),dict(characteristic_length_m=0),
                   dict(maximum_flow_L_s=float('nan')),dict(turndown=2),
                   dict(rows=[{'flow_L_s':20,'T025_m':1}]*2)]:
            with self.assertRaises(ValueError): self.run_case(**kw)


class TerminalProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalogue = self.root / 'catalogue.json'
        self.catalogue.write_text(json.dumps({'rows': [
            {'flow_L_s': 20, 'T025_m': 1}, {'flow_L_s': 100, 'T025_m': 5}]}), encoding='utf-8')
        self.project = self.root / 'project.json'
        self.data = dict(catalogue='catalogue.json',
                         catalogue_sha256=hashlib.sha256(self.catalogue.read_bytes()).hexdigest(),
                         basis='Synthetic input; applicability unreviewed', turndown=.4,
                         terminals=[dict(id='SD-1', maximum_flow_L_s=100,
                                         characteristic_lengths_m={'east': 2})])

    def execute(self):
        self.project.write_text(json.dumps(self.data), encoding='utf-8')
        return run(self.project, self.root / 'output')

    def test_saved_result_and_preserved_inputs(self):
        before = self.catalogue.read_bytes()
        result = self.execute()
        self.assertEqual(result['lookup_status'], 'within_catalogue')
        self.assertFalse(result['design_accepted'])
        self.assertEqual(self.catalogue.read_bytes(), before)
        self.assertEqual(json.loads((self.root / 'output/terminal-results.json').read_text()), result)
        with self.assertRaises(ValueError):
            run(self.project, self.root / 'output')

    def test_changed_catalogue_rejected_before_output(self):
        self.catalogue.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.execute()
        self.assertFalse((self.root / 'output').exists())

    def test_outside_retained(self):
        self.data['terminals'][0]['maximum_flow_L_s'] = 110
        result = self.execute()
        self.assertEqual(result['outside_catalogue_cases'], 1)
        self.assertEqual(result['lookup_status'], 'outside_catalogue')

    def test_duplicate_and_missing_directions_rejected(self):
        self.data['terminals'] *= 2
        with self.assertRaises(ValueError): self.execute()
        self.data['terminals'] = self.data['terminals'][:1]
        self.data['terminals'][0]['characteristic_lengths_m'] = {}
        with self.assertRaises(ValueError): self.execute()
        self.assertFalse((self.root / 'output').exists())
