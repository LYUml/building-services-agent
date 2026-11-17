"""The public recovery entry uses real adapters and an independent analytic root."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

from bsa import recovery_controller,workflow

ROOT=Path(__file__).resolve().parents[1]


class PumpRecoveryExampleTests(unittest.TestCase):
    def test_unsupported_objective_reports_the_exact_shared_contract(self):
        from bsa.pump_catalogue_iteration import candidates
        from bsa.engine import ProjectError
        data=json.loads((ROOT/'examples/pump-recovery/catalogue.json').read_text())
        data['objective']='Lowest declared preference among passing candidates'
        with self.assertRaisesRegex(ProjectError,"Catalogue objective must be exactly 'lowest declared preference among passing candidates'"):
            candidates(data)

    def example(self,folder):
        root=Path(folder)/'project';shutil.copytree(ROOT/'examples/pump-recovery',root)
        workflow.execute(root/'plan.json',root/'baseline')
        return root

    def test_recovery_meets_original_flow_and_independent_laminar_balance(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=self.example(folder)
            before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
            result=recovery_controller.run(root/'plan.json',root/'baseline',root/'policy.json',root/'recovery')
            verified=recovery_controller.verify(root/'recovery')
            self.assertTrue(verified['integrity_pass']);self.assertFalse(verified['execution_pass'])
            self.assertFalse(verified['design_accepted']);self.assertEqual(verified['steps'],1)
            self.assertEqual(result['steps'][0]['selected'],'adequate-analytic-curve')
            self.assertTrue(all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in before.items()))
            baseline=json.loads((root/'baseline/pump/pump.json').read_text())
            final=json.loads((Path(result['final_run'])/'pump/pump.json').read_text())
            self.assertFalse(baseline['calculated_checks_pass']);self.assertTrue(final['calculated_checks_pass'])
            old=baseline['operating_point'];point=final['operating_point']
            self.assertAlmostEqual(old['flow_m3_s'],1.2e-6,delta=1e-13)
            self.assertAlmostEqual(point['flow_m3_s'],2e-6,delta=1e-13)
            # Independent Poiseuille balance of the explicitly synthetic line.
            resistance=128*1*2/(math.pi*.01**4)
            self.assertAlmostEqual(point['pump_total_pressure_rise_pa'],100+resistance*2e-6,delta=.001)
            self.assertAlmostEqual(point['estimated_electrical_kw'],2e-6*(100+resistance*2e-6)/(.5*1000),delta=1e-10)
            self.assertEqual(json.loads(Path(result['final_plan']).read_text())['requirements'],json.loads((root/'plan.json').read_text())['requirements'])
            self.assertEqual(result['diagnosis']['recovery_schedule']['ready_tasks'],['review'])

    def test_no_feasible_catalogue_preserves_failed_baseline_and_stops(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=self.example(folder);path=root/'catalogue.json';data=json.loads(path.read_text())
            data['candidates'][0]['curve']=json.loads((root/'weak-curve.json').read_text())
            path.write_text(json.dumps(data),encoding='utf-8')
            result=recovery_controller.run(root/'plan.json',root/'baseline',root/'policy.json',root/'recovery')
            self.assertEqual(result['status'],'no_feasible_candidate')
            self.assertIsNone(result['steps'][0]['selected'])
            self.assertEqual(result['final_run'],str(root/'baseline'))
            self.assertTrue(recovery_controller.verify(root/'recovery')['integrity_pass'])
            self.assertFalse((root/'recovery-step-1-plan.json').exists())


if __name__=='__main__':unittest.main()
