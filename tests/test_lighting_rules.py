import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.regulations import evaluate

ROOT=Path(__file__).resolve().parents[1]


class LightingRuleTests(unittest.TestCase):
    def setUp(self):
        self.pack=json.loads((ROOT/'regulations/hk/lighting-2026.11.08/pack.json').read_text())
        self.project=json.loads((ROOT/'examples/regulations-hk-lighting/project.json').read_text())
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.pdf=self.root/'emsd-bec-2024.pdf'
        self.pdf.write_bytes(b'SYNTHETIC FIXTURE NOT OFFICIAL BEC');self.pack['sources']['emsd_bec_2024']['sha256']=digest(self.pdf)

    def check(self,area=20,power=120):
        space=self.project['lighting_space'];space['internal_floor_area']['value']=area
        space['luminaires']=space['luminaires'][:1];space['luminaires'][0]['full_output_circuit_power']['value']=power
        return evaluate(self.pack,self.project,self.root)['checks'][0]

    def test_exact_area_bands_and_limit_boundaries(self):
        for area,maximum in [(15,9),(15.01,8.5),(200,8.5),(200.01,7.2)]:
            with self.subTest(area=area):
                row=self.check(area,area*maximum);self.assertEqual(row['status'],'pass')
                self.assertEqual(row['maximum'],maximum)
                self.assertEqual(self.check(area,area*maximum+.01)['status'],'review_required')

    def test_low_power_exception_is_not_whole_compliance(self):
        row=self.check(1,70);self.assertEqual(row['status'],'not_applicable')
        self.assertEqual(self.check(1,70.01)['status'],'review_required')
        self.assertFalse(evaluate(self.pack,self.project,self.root)['design_accepted'])

    def test_inventory_full_watts_not_claimed_metric_or_dimming(self):
        self.project['facts']['office_full_output_lpd']=dict(value=0,unit='W/m2',source='false prefilled metric')
        self.project['lighting_space']['demand_factor']=.1
        r=evaluate(self.pack,self.project,self.root)['checks'][0]
        self.assertEqual(r['total_full_output_circuit_w'],120)
        self.assertEqual(r['computed_lpd_w_m2'],6)

    def test_missing_inventory_source_and_duplicate_ids_pending(self):
        lights=self.project['lighting_space']['luminaires'];lights[1]['id']=lights[0]['id']
        self.assertEqual(evaluate(self.pack,self.project,self.root)['checks'][0]['status'],'pending')
        lights[1]['id']='unique';del lights[0]['full_output_circuit_power']['source']
        self.assertEqual(evaluate(self.pack,self.project,self.root)['checks'][0]['status'],'pending')

    def test_scope_and_enclosed_classification_not_invented(self):
        self.project['facts']['enclosed_office']['value']=False
        self.assertEqual(self.check(15,120)['status'],'pending')
        self.project['facts']['enclosed_office']['value']=True
        del self.project['facts']['circuit_watts_include_controlgear_and_drivers']
        self.assertEqual(self.check()['status'],'pending')

    def test_changed_official_source_pending(self):
        self.pdf.write_bytes(b'changed');self.assertEqual(self.check()['status'],'pending')
