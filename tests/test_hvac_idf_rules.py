import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.energy import build, validate
from bsa.engine import ProjectError
from bsa.hvac_idf_rules import extract, run

ROOT=Path(__file__).resolve().parents[1]


class NativeHVACRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.project=json.loads((ROOT/'examples/sizing-humidity/project.json').read_text())
        self.bases=json.loads((ROOT/'examples/regulations-hk-hvac/zone-bases.json').read_text())
        build(validate(self.project),12,self.root)
        self.idf=self.root/'model.idf'

    def test_native_extrema_and_zone_coverage(self):
        rows=extract(self.idf,self.bases)
        self.assertEqual(set(rows),{'Zone 1','Zone 2'})
        for days in rows.values():
            self.assertEqual(len(days),2)
            self.assertEqual(days['Synthetic winter']['load_design_conditions']['outdoor_dry_bulb']['value'],5)
            summer=days['Synthetic summer']['load_design_conditions']
            self.assertEqual(summer['indoor_dry_bulb']['value'],24)
            self.assertEqual(summer['indoor_relative_humidity']['value'],50)
            self.assertIn(digest(self.idf),summer['indoor_dry_bulb']['source'])

    def test_missing_zone_and_numeric_override_rejected(self):
        bad=copy.deepcopy(self.bases);del bad['Zone 1']
        with self.assertRaisesRegex(ProjectError,'coverage'):extract(self.idf,bad)
        bad=copy.deepcopy(self.bases);bad['Zone 1']['load_design_conditions']['outdoor_dry_bulb']={'value':7}
        with self.assertRaisesRegex(ProjectError,'cannot be overridden'):extract(self.idf,bad)

    def test_changed_native_controls_rejected(self):
        original=self.idf.read_text()
        for old,new,reason in [('Sensible And Latent Load','Sensible Load Only No Latent Load','latent sizing'),
                               ('Until: 24:00','Until: 12:00','control type')]:
            self.assertIn(old,original)
            self.idf.write_text(original.replace(old,new))
            with self.subTest(new=new),self.assertRaisesRegex(ProjectError,reason):extract(self.idf,self.bases)

    def test_rule_failure_then_independent_native_revision(self):
        pack=json.loads((ROOT/'regulations/hk/hvac-design-2026.11.08/pack.json').read_text())
        pdf=self.root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE ONLY')
        pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
        pp=self.root/'pack.json';pp.write_text(json.dumps(pack))
        bp=self.root/'bases.json';bp.write_text(json.dumps(self.bases))
        failed=run(self.idf,bp,pp,self.root,self.root/'negative')
        self.assertFalse(failed['supported_checks_pass'])
        for days in failed['zone_design_day_checks'].values():
            self.assertEqual(days['Synthetic winter']['checks'][0]['status'],'review_required')
            self.assertEqual(days['Synthetic summer']['checks'][0]['status'],'pass')
        revised=copy.deepcopy(self.project)
        revised['design_days'][1].update(max_dry_bulb_c=7,range_c=0)
        folder=self.root/'revised';folder.mkdir();build(validate(revised),12,folder)
        passed=run(folder/'model.idf',bp,pp,self.root,self.root/'positive')
        self.assertTrue(passed['supported_checks_pass']);self.assertFalse(passed['design_accepted'])
        pdf.write_bytes(b'changed')
        changed=run(folder/'model.idf',bp,pp,self.root,self.root/'changed-source')
        self.assertFalse(changed['supported_checks_pass'])


if __name__=='__main__':unittest.main()
