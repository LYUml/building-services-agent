import copy
import json
from pathlib import Path
import tempfile
import unittest

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.regulations import evaluate

ROOT=Path(__file__).resolve().parents[1]


class RegulationPackTests(unittest.TestCase):
    def setUp(self):
        self.pack=json.loads((ROOT/'regulations/hk/2026.11.08/pack.json').read_text())
        self.project=json.loads((ROOT/'examples/regulations-hk/project.json').read_text())
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.file=self.root/'emsd-wiring-2025.pdf';self.file.write_bytes(b'Synthetic source fixture, NOT an official regulation PDF')
        self.pack['sources']['emsd_wiring_2025']['sha256']=digest(self.file)

    def status(self):return evaluate(self.pack,self.project,self.root)['checks'][0]['status']

    def test_boundary_and_alternative_path_do_not_claim_compliance(self):
        metric=self.project['facts']['installation_origin_to_fixed_equipment_voltage_drop']
        metric['value']=4;self.assertEqual(self.status(),'pass')
        metric['value']=4.001;self.assertEqual(self.status(),'review_required')
        result=evaluate(self.pack,self.project,self.root)
        self.assertFalse(result['design_accepted'])
        self.assertEqual(result['regulatory_compliance'],'not_established')

    def test_missing_fact_or_edition_never_passes(self):
        for field in ('facts','edition_decisions'):
            with self.subTest(field=field):
                project=copy.deepcopy(self.project);project[field]={}
                self.assertFalse(evaluate(self.pack,project,self.root)['supported_checks_pass'])

    def test_changed_official_bytes_block_check(self):
        self.file.write_bytes(b'changed fixture')
        self.assertEqual(self.status(),'pending')

    def test_branch_only_and_starting_scope_do_not_reuse_normal_total_limit(self):
        for field in ('normal_service','includes_entire_installation_origin_to_equipment_path'):
            project=copy.deepcopy(self.project);project['facts'][field]['value']=False
            result=evaluate(self.pack,project,self.root)
            self.assertEqual(result['checks'][0]['status'],'not_applicable')
            self.assertFalse(result['supported_checks_pass'])

    def test_wrong_unit_and_nonfinite_value_are_pending(self):
        for change in ({'unit':'V'},{'value':True},{'value':float('nan')},{'source':''}):
            project=copy.deepcopy(self.project);project['facts']['installation_origin_to_fixed_equipment_voltage_drop'].update(change)
            self.assertEqual(evaluate(self.pack,project,self.root)['checks'][0]['status'],'pending')

    def test_packs_are_explicitly_pinned_and_methods_cannot_execute_code(self):
        self.project['jurisdiction']='OTHER'
        with self.assertRaises(ProjectError):self.status()
        self.project['jurisdiction']='HK';self.pack['rules'][0]['method']='eval'
        with self.assertRaises(ProjectError):self.status()
