import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.regulations import evaluate

ROOT=Path(__file__).resolve().parents[1]


class HVACRuleTests(unittest.TestCase):
    def setUp(self):
        self.pack=json.loads((ROOT/'regulations/hk/hvac-design-2026.11.08/pack.json').read_text())
        self.project=json.loads((ROOT/'examples/regulations-hk-hvac/project.json').read_text())
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.pdf=self.root/'emsd-bec-2024.pdf'
        self.pdf.write_bytes(b'SYNTHETIC TEST SOURCE NOT AN OFFICIAL PDF');self.pack['sources']['emsd_bec_2024']['sha256']=digest(self.pdf)

    def set(self,**values):
        for k,v in values.items():self.project['load_design_conditions'][k]['value']=v

    def status(self):return evaluate(self.pack,self.project,self.root)['checks'][0]['status']

    def test_summer_classification_and_indoor_limits(self):
        for app,minimum in [('office',23),('classroom',23),('hotel',22),('other',22)]:
            self.set(application=app,indoor_dry_bulb=minimum)
            self.assertEqual(self.status(),'pass')
            self.set(indoor_dry_bulb=minimum-.01);self.assertEqual(self.status(),'review_required')
        self.set(indoor_dry_bulb=23,indoor_relative_humidity=49.99)
        self.assertEqual(self.status(),'review_required')

    def test_summer_outdoor_joint_corner_and_limits(self):
        for db,wb,expected in [(35,28.99,'pass'),(34.99,29,'pass'),(35,29,'review_required'),(35.01,28,'review_required'),(34,29.01,'review_required')]:
            self.set(outdoor_dry_bulb=db,outdoor_wet_bulb=wb)
            with self.subTest(db=db,wb=wb):self.assertEqual(self.status(),expected)

    def test_winter_hotel_other_and_outdoor_boundary(self):
        self.set(season='winter',outdoor_dry_bulb=7,application='hotel',indoor_dry_bulb=24)
        self.assertEqual(self.status(),'pass')
        self.set(application='office');self.assertEqual(self.status(),'review_required')
        self.set(indoor_dry_bulb=22);self.assertEqual(self.status(),'pass')
        self.set(outdoor_dry_bulb=6.99);self.assertEqual(self.status(),'review_required')
        self.set(outdoor_dry_bulb=7,indoor_relative_humidity=50.01);self.assertEqual(self.status(),'review_required')

    def test_missing_design_inputs_cannot_be_replaced_by_thermostat(self):
        del self.project['load_design_conditions']['indoor_dry_bulb']
        self.project['thermostat_cooling_setpoint_c']=23
        self.assertEqual(self.status(),'pending')

    def test_nonphysical_units_and_unsupported_scope_preserved(self):
        self.set(outdoor_dry_bulb=20,outdoor_wet_bulb=28);self.assertEqual(self.status(),'pending')
        self.set(outdoor_dry_bulb=35,indoor_relative_humidity=101);self.assertEqual(self.status(),'pending')
        self.set(indoor_relative_humidity=50)
        self.project['facts']['human_comfort_application']['value']=False
        self.assertEqual(self.status(),'not_applicable')
        self.project['facts']['human_comfort_application']['value']=True
        self.project['load_design_conditions']['indoor_dry_bulb']['unit']='degF';self.assertEqual(self.status(),'pending')

    def test_changed_source_and_missing_edition_pending(self):
        self.pdf.write_bytes(b'changed');self.assertEqual(self.status(),'pending')
        self.pdf.write_bytes(b'SYNTHETIC TEST SOURCE NOT AN OFFICIAL PDF')
        self.project['edition_decisions']={};self.assertEqual(self.status(),'pending')
