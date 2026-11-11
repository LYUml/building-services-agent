import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.workflow import execute
from bsa.delivery import context
from bsa.module_fan import verify
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class ModularFanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('modular-fan-plan.json','modular/fan-brief.md','modular/bound-air-authoring.json','modular/bound-air-budget.json','rectangular-air/straight-wall.json','rectangular-air/binding-project.json','rectangular-air/binding.json','rectangular-air/fan-curve.json'):
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/'examples'/name).read_bytes())
        self.plan=self.root/'modular-fan-plan.json'

    def network_change(self,change):
        path=self.root/'rectangular-air/binding-project.json';data=json.loads(path.read_text());change(data);path.write_text(json.dumps(data))
        request=self.root/'modular/bound-air-budget.json';r=json.loads(request.read_text());r['sources']['project']['sha256']=digest(path);request.write_text(json.dumps(r))

    def test_inherits_exact_native_network_and_preserves_power_semantics(self):
        out=self.root/'run';r=execute(self.plan,out);fan=verify(out/'fan')
        self.assertEqual([t['status'] for t in r['tasks'].values()],['pass','pass','pass','pending'])
        budget=json.loads((out/'budget/exchange/result.json').read_text())
        self.assertIn('network_input',budget['payload']);self.assertAlmostEqual(budget['payload']['supply_flow_m3_s'],.5)
        self.assertGreater(fan['operating_point']['flow_m3_s'],.5);self.assertIn('air_power_kw',fan['operating_point'])
        self.assertNotIn('estimated_electrical_kw',fan['operating_point']);self.assertFalse(fan['design_accepted'])
        original=(out/'fan/fan.json').read_text()
        fan['operating_point']['air_power_kw']=1000;(out/'fan/fan.json').write_text(json.dumps(fan))
        with self.assertRaisesRegex(ValueError,'differs from inherited-source replay'):verify(out/'fan')
        fan=json.loads(original);fan['trace'][0]['residual_pa']+=10;(out/'fan/fan.json').write_text(json.dumps(fan))
        with self.assertRaisesRegex(ValueError,'differs from inherited-source replay'):verify(out/'fan')

    def test_converged_insufficient_capacity_stays_failed_and_blocks_review(self):
        self.network_change(lambda p:p['nodes'][1].update(demand_m3_s=.8));out=self.root/'capacity';r=execute(self.plan,out);fan=verify(out/'fan')
        self.assertEqual(fan['status'],'converged');self.assertFalse(fan['calculated_checks_pass'])
        self.assertEqual(r['tasks']['budget']['status'],'pass');self.assertEqual(r['tasks']['fan']['status'],'fail')
        self.assertEqual(diagnose(self.plan,out)['tasks'][3]['blocked_by'],['fan'])
        r['tasks']['fan']['status']='pass'
        for row in r['requirements']:
            if row['task']=='fan':row['execution_status']='pass'
        (out/'workflow.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'fan status contradicts'):context(self.plan,out)

    def test_no_intersection_retains_curve_failure(self):
        path=self.root/'rectangular-air/fan-curve.json';c=json.loads(path.read_text())
        for point in c['points']:point['total_pressure_rise_pa']*=.1
        path.write_text(json.dumps(c));out=self.root/'no-root';r=execute(self.plan,out);fan=verify(out/'fan')
        self.assertFalse(fan['calculated_checks_pass']);self.assertIsNone(fan['operating_point']);self.assertEqual(r['tasks']['fan']['status'],'fail')
        self.assertFalse((out/'fan/operating-network.json').exists())

    def test_failed_budget_never_invokes_fan_or_fabricates_output(self):
        self.network_change(lambda p:p['supply'].update(total_pressure_pa=0));out=self.root/'upstream'
        with patch('bsa.module_fan.run') as fan:r=execute(self.plan,out)
        fan.assert_not_called();self.assertEqual([t['status'] for t in r['tasks'].values()],['pass','fail','pending','pending'])
        self.assertFalse((out/'fan').exists())
