import json
import copy
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.modules import run,verify_result
from bsa.workflow import execute,verify
from bsa.delivery import context

ROOT=Path(__file__).resolve().parents[1]


class ModularElectricalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ('modular-electrical-plan.json','modular/electrical-request.json','modular/electrical-brief.md','office-electrical/project.json'):
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/'examples'/name).read_bytes())
        self.request=self.root/'modular/electrical-request.json';self.project=self.root/'office-electrical/project.json';self.plan=self.root/'modular-electrical-plan.json'

    def test_actual_provider_replay_units_and_valid_payload_forgery(self):
        out=self.root/'module';r=run(self.request,'bsa.single-phase-circuits',out);verify_result(out/'result.json')
        self.assertEqual(r['execution']['status'],'completed');self.assertEqual(r['payload']['status'],'pass')
        self.assertEqual(r['payload']['units']['real_power'],'kW electrical');self.assertFalse(r['payload']['geometry_bound'])
        self.assertEqual(r['acceptance']['status'],'pending')
        r['payload']['circuits'][0]['voltage_drop_v']+=1;(out/'result.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'payload differs'):verify_result(out/'result.json')

    def test_numerical_failure_and_disable_block_dependents(self):
        data=json.loads(self.project.read_text());data['circuits'][0]['breaker_a']=0.1;self.project.write_text(json.dumps(data))
        request=json.loads(self.request.read_text());request['sources']['project']['sha256']=digest(self.project);self.request.write_text(json.dumps(request))
        out=self.root/'failure';r=execute(self.plan,out)
        self.assertEqual(r['tasks']['electrical']['status'],'fail');self.assertIn('required checks unresolved',r['tasks']['review']['scope'])
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        out=self.root/'disabled';r=execute(self.plan,out,disabled_module_providers=['bsa.single-phase-circuits'])
        self.assertEqual(r['tasks']['electrical']['status'],'pending');context(self.plan,out)
        self.assertIsNone(json.loads((out/'electrical/result.json').read_text())['payload'])

    def test_source_replay_rejects_coherently_rehashed_report_change(self):
        out=self.root/'changed';r=run(self.request,'bsa.single-phase-circuits',out)
        report=out/'analysis/calculations.json';data=json.loads(report.read_text());data['circuits'][0]['design_current_a']+=1;report.write_text(json.dumps(data))
        r['artifacts']['analysis/calculations.json']=digest(report);r['payload']['report']['sha256']=digest(report)
        (out/'result.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'source replay'):verify_result(out/'result.json')

    def test_common_contract_keeps_units_phase_totals_and_unique_circuits(self):
        from bsa.module_contract import validate
        result=run(self.request,'bsa.single-phase-circuits',self.root/'contract')['payload']
        changed=copy.deepcopy(result);changed['units']['real_power']='kW thermal'
        with self.assertRaises(ValueError):validate(changed)
        changed=copy.deepcopy(result);changed['phase_demand_va']['L1']+=1
        with self.assertRaisesRegex(ValueError,'phase apparent-power'):validate(changed)
        changed=copy.deepcopy(result);changed['circuits'].append(copy.deepcopy(changed['circuits'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate common circuit'):validate(changed)

    def test_unknown_load_semantics_reject_before_calculation_artifacts(self):
        original=json.loads(self.project.read_text());request=json.loads(self.request.read_text())
        for name,key,value in [('three-phase','phase_count',3),('thermal','thermal_kw',5),('line-voltage','line_to_line_voltage_v',400)]:
            data=copy.deepcopy(original);data['devices'][0][key]=value;self.project.write_text(json.dumps(data))
            request['sources']['project']['sha256']=digest(self.project);self.request.write_text(json.dumps(request))
            out=self.root/name;r=run(self.request,'bsa.single-phase-circuits',out)
            self.assertEqual(r['execution']['status'],'failed');self.assertIsNone(r['payload'])
            self.assertIn('Unsupported devices fields',r['execution']['diagnostics'][0]['message'])
            self.assertEqual(r['execution']['diagnostics'][0]['code'],'unsupported_source_semantics')
            self.assertFalse((out/'analysis').exists());verify_result(out/'result.json')
        from bsa.workflow_status import diagnose
        out=self.root/'scope-workflow';execute(self.plan,out)
        self.assertIn('without deleting fields',diagnose(self.plan,out)['actions'][0]['next_action'])

    def test_rehashed_schematic_geometry_identity_and_style_changes_reject(self):
        import ezdxf
        for change in ('position','identity','rotation'):
            out=self.root/('schematic-'+change);r=run(self.request,'bsa.single-phase-circuits',out)
            path=out/'analysis/devices.dxf';doc=ezdxf.readfile(path)
            if change=='position':doc.modelspace().query('CIRCLE')[0].dxf.center=(99,99,0)
            elif change=='identity':doc.modelspace().query('TEXT')[0].dxf.text='OTHER / CIRCUIT'
            else:doc.modelspace().query('TEXT')[0].dxf.rotation=45
            doc.saveas(path);r['artifacts']['analysis/devices.dxf']=digest(path);r['payload']['schematic_dxf']['sha256']=digest(path);(out/'result.json').write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'schematic'):verify_result(out/'result.json')
