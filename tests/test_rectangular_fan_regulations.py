import json
from pathlib import Path
import runpy
import tempfile
import unittest
import ifcopenshell
from bsa.rectangular_fan_regulations import run
from bsa.workflow import validate_plan
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'runs/hk-fan-sources-v1'


@unittest.skipUnless((CACHE/'emsd-bec-2024.pdf').is_file() and (CACHE/'emsd-tg-bec-2024.pdf').is_file(),'requires pinned official BEC/TG cache')
class RectangularFanRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.demo=runpy.run_path(str(ROOT/'scripts/run_rectangular_hk_fan_demo.py'))['run'](cls.root/'suite',CACHE)
        cls.stage=cls.root/'suite';cls.producer=cls.stage/'workflow/model';cls.base=cls.producer/'selected-coordination'

    def invoke(self,**changes):
        paths=dict(project=self.base/'network-input.json',model=self.producer/'selected-model.json',binding=self.stage/'binding.json',ifc=self.base/'bim/model.ifc',analysis=self.base/'analysis/network.json',basis=self.stage/'pass.json',pack=self.stage/'fan-pack.json',sources=self.stage/'sources',out=self.root/self._testMethodName)
        paths.update(changes);return run(**paths)

    def test_actual_three_cases_and_derived_denominator(self):
        states={t['id']:t['status'] for t in self.demo['tasks']}
        self.assertEqual([states[k] for k in ('model','pass','exceeded','unknown-supply')],['pass','pass','fail','pending'])
        r=self.invoke();self.assertEqual(r['fresh_supply_design_flow_l_s'],2000.)
        self.assertEqual(r['rule_result']['checks'][0]['maximum_unadjusted_power_w'],3200.)
        self.assertFalse(r['design_accepted'])

    def test_supply_flow_override_rejected(self):
        p=json.loads((self.stage/'pass.json').read_text());p['facts']['supply_design_airflow']=dict(value=1e6,unit='L/s',source='Unrelated flow')
        path=self.root/'override.json';path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'override forbidden'):self.invoke(basis=path)

    def test_saved_study_flow_tamper_rejected(self):
        p=json.loads((self.base/'analysis/network.json').read_text());p['supply_flow_m3_s']=20
        path=self.root/'false-study.json';path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'fresh analysis'):self.invoke(analysis=path)

    def test_saved_native_section_tamper_rejected(self):
        m=ifcopenshell.open(str(self.base/'bim/model.ifc'));m.by_type('IfcDuctSegment')[0].Representation.Representations[0].Items[0].SweptArea.XDim+=.01
        path=self.root/'false-model.ifc';m.write(str(path))
        with self.assertRaises(ProjectError):self.invoke(ifc=path)

    def test_missing_motor_evidence_remains_pending(self):
        p=json.loads((self.stage/'pass.json').read_text());p['facts'].pop('fan_motor_power');path=self.root/'missing-power.json';path.write_text(json.dumps(p))
        self.assertEqual(self.invoke(basis=path)['status'],'pending')

    def test_drawing_cannot_use_other_producer_fan_gate(self):
        p=json.loads((self.stage/'plan.json').read_text());other=dict(p['tasks'][0],id='other');p['tasks'].insert(1,other)
        policy=self.stage/'policy.json';policy.write_bytes((ROOT/'examples/rectangular-air/clash-policy.json').read_bytes())
        p['tasks'].extend([dict(id='coord',kind='ifc_clash',depends_on='other',policy='policy.json'),dict(id='drawing',kind='rectangular_drawing',depends_on='other',requires_pass=['coord','pass'],settings='unused.json',sheet='unused-sheet.json')])
        path=self.stage/'wrong-producer-plan.json';path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'different native producer'):validate_plan(path)
