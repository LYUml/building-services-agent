import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.regulations import evaluate
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class FanPowerRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.pack=json.loads((ROOT/'regulations/hk/fan-power-2026.11.10/pack.json').read_text());self.project=json.loads((ROOT/'examples/hk-fan-power/project.json').read_text())
        for source in self.pack['sources'].values():
            path=self.root/source['cache_filename'];path.write_text('Test-only byte fixture, not official evidence');source['sha256']=digest(path)

    def check(self):return evaluate(self.pack,self.project,self.root)['checks'][0]

    def test_cav_vav_inclusive_limits_and_over_limit(self):
        for mode,power in [('CAV',3200.),('VAV',4200.)]:
            self.project['facts']['air_distribution_mode']['value']=mode;self.project['facts']['fan_motor_power']['value']=power
            self.assertEqual(self.check()['status'],'pass')
            self.project['facts']['fan_motor_power']['value']=power+.01
            self.assertEqual(self.check()['status'],'review_required')

    def test_strict_2500w_exemption_boundary(self):
        self.project['facts']['supply_design_airflow']['value']=1000.
        self.project['facts']['fan_motor_power']['value']=2499.999
        self.assertEqual(self.check()['status'],'not_applicable')
        self.project['facts']['fan_motor_power']['value']=2500.
        self.assertEqual(self.check()['status'],'review_required')

    def test_asserted_exemptions_do_not_clear_other_hvac_requirements(self):
        for key in ('ahu_individual_fan_exemption_applies','schedule2_exemption_applies'):
            self.project['facts'][key]['value']=True
            self.assertEqual(self.check()['status'],'not_applicable')
            self.assertFalse(evaluate(self.pack,self.project,self.root)['supported_checks_pass'])
            self.project['facts'][key]['value']=False

    def test_missing_inventory_or_motor_basis_stays_pending(self):
        for key in ('fan_inventory_complete','motor_power_drawn_clean_basis_confirmed','ahu_individual_fan_exemption_applies'):
            p=copy.deepcopy(self.project);self.project['facts'][key]['value']=None
            self.assertEqual(self.check()['status'],'pending');self.project=p

    def test_no_pressure_to_watts_or_nameplate_substitution(self):
        self.project['facts']['fan_motor_power']['unit']='Pa';self.assertEqual(self.check()['status'],'pending')
        self.project['facts']['fan_motor_power']['unit']='W';self.project['facts']['motor_power_drawn_clean_basis_confirmed']['value']=False
        self.assertNotEqual(self.check()['status'],'pass')

    def test_treatment_adjustment_not_silently_applied(self):
        self.project['facts']['clean_treatment_pressure_drop']['value']=251.
        row=self.check();self.assertEqual(row['status'],'pending');self.assertEqual(row['deduction_applied_w'],0)

    def test_both_official_sources_and_editions_required(self):
        path=self.root/'emsd-tg-bec-2024.pdf';path.write_text('changed')
        self.assertEqual(self.check()['status'],'pending')
        self.pack['sources']['emsd_tg_bec_2024']['sha256']=digest(path);self.project['edition_decisions'].pop('emsd_tg_bec_2024')
        self.assertEqual(self.check()['status'],'pending')

    def test_changed_limits_rejected(self):
        self.pack['rules'][0]['limits']['CAV']=2.
        with self.assertRaises(ProjectError):self.check()

    def test_guidance_is_in_runtime_source_inventory(self):
        from bsa.regulations import source_paths,method_paths
        self.assertEqual({p.name for p in source_paths(self.pack,self.root)},{'emsd-bec-2024.pdf','emsd-tg-bec-2024.pdf'})
        self.assertIn('fan_power_rules.py',{p.name for p in method_paths(self.pack)})
