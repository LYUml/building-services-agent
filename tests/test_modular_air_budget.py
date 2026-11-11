import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.modules import verify_result
from bsa.workflow import execute
from bsa.workflow_status import diagnose
from bsa.delivery import context
from bsa.module_contract import validate

ROOT=Path(__file__).resolve().parents[1]


class ModularAirBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('modular-analysis-plan.json','modular/air-budget.json','modular/air-budget-brief.md','rectangular-air/project.json'):
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/'examples'/name).read_bytes())
        self.plan=self.root/'modular-analysis-plan.json'

    def pressure(self,value):
        path=self.root/'rectangular-air/project.json';p=json.loads(path.read_text());p['supply']['total_pressure_pa']=value;path.write_text(json.dumps(p))
        request=self.root/'modular/air-budget.json';data=json.loads(request.read_text());data['sources']['project']['sha256']=digest(path);request.write_text(json.dumps(data))

    def test_actual_budget_preserves_units_raw_report_and_unaccepted_design(self):
        out=self.root/'pass';r=execute(self.plan,out);m=verify_result(out/'budget/result.json')
        self.assertEqual(r['tasks']['budget']['status'],'pass');self.assertEqual(m['execution']['status'],'completed')
        self.assertEqual(m['payload']['units'],dict(flow='m3/s',pressure='Pa',velocity='m/s'))
        self.assertAlmostEqual(m['payload']['supply_flow_m3_s'],.5);self.assertFalse(m['payload']['geometry_bound'])
        self.assertTrue((out/'budget/analysis/segments.csv').is_file());self.assertFalse(r['design_accepted'])

    def test_completed_failed_pressure_blocks_review_and_rejects_false_workflow_pass(self):
        self.pressure(0);out=self.root/'low';r=execute(self.plan,out);m=verify_result(out/'budget/result.json')
        self.assertEqual(m['execution']['status'],'completed');self.assertEqual(m['payload']['status'],'fail')
        self.assertEqual(r['tasks']['budget']['status'],'fail');self.assertEqual(r['tasks']['review']['status'],'pending')
        d=diagnose(self.plan,out);self.assertIn('failed declared numerical checks',d['actions'][0]['next_action'])
        self.assertEqual(d['tasks'][0]['module_state']['numerical_result']['status'],'fail')
        r['tasks']['budget']['status']='pass'
        for row in r['requirements']:
            if row['task']=='budget':row['execution_status']='pass'
        (out/'workflow.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'contradicts retained module'):context(self.plan,out)

    def test_disabled_analysis_and_invalid_domain_input_are_distinct(self):
        out=self.root/'disabled';r=execute(self.plan,out,disabled_module_providers=['fluids.rectangular-air-budget'])
        self.assertEqual(r['tasks']['budget']['status'],'pending');self.assertIsNone(verify_result(out/'budget/result.json')['payload'])
        path=self.root/'rectangular-air/project.json';p=json.loads(path.read_text());p['segments'][0]['width_m']=0;path.write_text(json.dumps(p))
        request=self.root/'modular/air-budget.json';data=json.loads(request.read_text());data['sources']['project']['sha256']=digest(path);request.write_text(json.dumps(data))
        out=self.root/'invalid';r=execute(self.plan,out);m=verify_result(out/'budget/result.json')
        self.assertEqual(m['execution']['status'],'failed');self.assertIsNone(m['payload']);self.assertEqual(r['tasks']['budget']['status'],'fail')

    def test_common_check_forgery_and_wrong_units_reject(self):
        self.pressure(0);out=self.root/'forgery';execute(self.plan,out);path=out/'budget/result.json';r=json.loads(path.read_text())
        r['payload']['status']='pass'
        with self.assertRaises(ValueError):validate(r)
        r['payload']['checks']={k:True for k in r['payload']['checks']};path.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'retained engine result'):verify_result(path)
        r['payload']['units']['pressure']='kW'
        with self.assertRaises(ValueError):validate(r)
