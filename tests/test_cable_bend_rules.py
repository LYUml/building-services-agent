import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.regulations import evaluate
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class CableBendTableTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.pack=json.loads((ROOT/'regulations/hk/cable-bends-2026.11.10/pack.json').read_text())
        source=self.root/'emsd-wiring-2025.pdf';source.write_text('Unit-test byte integrity fixture only, not official regulatory evidence')
        self.pack['sources']['emsd_wiring_2025']['sha256']=digest(source)
        facts={key:dict(value=True,source='Explicit synthetic test classification') for key in ('wiring_scope_confirmed','low_voltage','pvc_insulated','stranded_copper')}
        facts.update(armoured=dict(value=False,source='Test armour classification'),overall_diameter=dict(value=20.,unit='mm',source='Test overall diameter'),internal_bend_radius=dict(value=80.,unit='mm',source='Test actual internal radius'))
        self.project=dict(jurisdiction='HK',rule_pack=self.pack['id'],edition_decisions={'emsd_wiring_2025':dict(edition='2025',basis='Synthetic edition choice')},facts=facts)

    def check(self):return evaluate(self.pack,self.project,self.root)['checks'][0]

    def test_diameter_bands_and_inclusive_boundaries(self):
        for diameter,factor in [(9.,3),(10.,3),(10.000001,4),(25.,4),(25.000001,6),(40.,6)]:
            self.project['facts']['overall_diameter']['value']=diameter
            self.project['facts']['internal_bend_radius']['value']=diameter*factor
            row=self.check();self.assertEqual(row['status'],'pass');self.assertEqual(row['multiplier'],factor)

    def test_armoured_factor_all_sizes(self):
        self.project['facts']['armoured']['value']=True
        for diameter in (5.,10.,20.,25.,40.):
            self.project['facts']['overall_diameter']['value']=diameter;self.project['facts']['internal_bend_radius']['value']=6*diameter
            self.assertEqual(self.check()['multiplier'],6);self.assertEqual(self.check()['status'],'pass')

    def test_just_below_limit_requires_review(self):
        self.project['facts']['internal_bend_radius']['value']=79.999999
        self.assertEqual(self.check()['status'],'review_required')

    def test_unknown_classification_or_armour_pending(self):
        for key in ('pvc_insulated','stranded_copper','armoured','low_voltage'):
            old=self.project['facts'][key]['value'];self.project['facts'][key]['value']=None
            self.assertEqual(self.check()['status'],'pending');self.project['facts'][key]['value']=old

    def test_hv_and_non_pvc_not_cleared(self):
        for key in ('low_voltage','pvc_insulated'):
            self.project['facts'][key]['value']=False
            row=self.check();self.assertEqual(row['status'],'not_applicable')
            self.assertFalse(evaluate(self.pack,self.project,self.root)['supported_checks_pass'])
            self.project['facts'][key]['value']=True

    def test_wrong_unit_or_missing_edition_pending(self):
        self.project['facts']['internal_bend_radius']['unit']='m';self.assertEqual(self.check()['status'],'pending')
        self.project['facts']['internal_bend_radius']['unit']='mm';self.project['edition_decisions']={}
        self.assertEqual(self.check()['status'],'pending')

    def test_changed_official_bytes_pending(self):
        (self.root/'emsd-wiring-2025.pdf').write_text('changed bytes')
        self.assertEqual(self.check()['status'],'pending')

    def test_changed_table_rejected(self):
        self.pack['rules'][0]['limits']['armoured_factor']=3
        with self.assertRaisesRegex(ProjectError,'verified CoP'):self.check()
