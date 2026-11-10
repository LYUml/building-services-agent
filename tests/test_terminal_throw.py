import unittest
from bsa.terminal_throw import evaluate


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
