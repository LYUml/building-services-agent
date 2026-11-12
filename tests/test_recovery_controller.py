import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa import recovery_controller as controller,workflow
from bsa.workflow_draft import draft
from tests.test_pump import case

ROOT=Path(__file__).resolve().parents[1]

class RecoveryControllerTests(unittest.TestCase):
    def setUp(self):
        saved=os.environ.get('BSA_RECOVERY_TRIAL_OUT') if self._testMethodName=='test_two_ready_failures_are_repaired_with_fresh_diagnosis' else None
        if saved:
            self.root=Path(saved).resolve()
            if not self.root.is_relative_to(ROOT/'runs') or self.root.exists():raise ValueError('Fresh repository run required')
            self.root.mkdir(parents=True)
        else:
            temporary=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        brief=self.root/'brief.md';brief.write_text('Calculate the first synthetic pump scenario at its original minimum flow.\n\nCalculate the independent second synthetic pump scenario at its original minimum flow.\n\nReview real equipment and installation; these analytic scenarios are not an installed system.')
        self.plan=self.root/'plan.json';draft(brief,self.plan);source=json.loads(self.plan.read_text())
        network,weak,_=case(1.2e-6);_,good,_=case()
        for name,value in [('network.json',network),('weak.json',weak)]: (self.root/name).write_text(json.dumps(value))
        source['tasks']=[dict(id=t,kind='pump_operating_point',project='network.json',curve='weak.json') for t in ['first','second']]+[dict(id='review',kind='manual',requires_pass=['first','second'])]
        for row,task in zip(source['requirements'],['first','second','review']):row.update(task=task,acceptance=row['quote'])
        source['unresolved_inputs']=[];self.plan.write_text(json.dumps(source))
        self.original=self.root/'original';workflow.execute(self.plan,self.original)
        self.catalogue=dict(objective='lowest declared preference among passing candidates',source='Explicit synthetic analytic scenarios, not actual products',candidates=[dict(id='eligible',source='Synthetic adequate curve',preference=1,curve=good)])
        (self.root/'catalogue.json').write_text(json.dumps(self.catalogue))
        self.data=dict(schema='bsa.recovery-policy/1',max_steps=4,actions=[dict(task=t,catalogue='catalogue.json') for t in ['first','second']])
        self.policy=self.root/'policy.json';self.out=self.root/'controller'

    def run_controller(self):
        self.policy.write_text(json.dumps(self.data))
        return controller.run(self.plan,self.original,self.policy,self.out)

    def test_two_ready_failures_are_repaired_with_fresh_diagnosis(self):
        before=self.plan.read_bytes();failure=(self.original/'workflow.json').read_bytes()
        result=self.run_controller();checked=controller.verify(self.out)
        self.assertEqual([r['task'] for r in result['steps']],['first','second'])
        self.assertEqual(checked['steps'],2);self.assertEqual(checked['status'],'needs_action_or_review')
        self.assertEqual(result['diagnosis']['recovery_schedule']['ready_tasks'],['review'])
        self.assertEqual([r['status'] for r in result['diagnosis']['tasks']],['pass','pass','pending'])
        self.assertFalse(checked['design_accepted']);self.assertFalse(checked['execution_pass'])
        self.assertEqual(self.plan.read_bytes(),before);self.assertEqual((self.original/'workflow.json').read_bytes(),failure)
        self.assertEqual(json.loads(Path(result['final_plan']).read_text())['requirements'],json.loads(before)['requirements'])

    def test_step_limit_retains_other_ready_failure(self):
        self.data['max_steps']=1;result=self.run_controller()
        self.assertEqual(result['status'],'step_limit');self.assertEqual(controller.verify(self.out)['steps'],1)
        self.assertIn('second',result['diagnosis']['recovery_schedule']['ready_tasks'])

    def test_no_feasible_candidate_stops_before_other_action(self):
        _,weak,_=case(1.2e-6);self.catalogue['candidates'][0]['curve']=weak
        (self.root/'catalogue.json').write_text(json.dumps(self.catalogue))
        result=self.run_controller();self.assertEqual(result['status'],'no_feasible_candidate')
        self.assertEqual(controller.verify(self.out)['steps'],1)
        self.assertFalse((self.out/'step-2').exists());self.assertEqual(result['final_plan'],str(self.plan))

    def test_undeclared_failures_and_manual_reviews_are_not_repaired(self):
        self.data['actions']=[];result=self.run_controller()
        self.assertEqual(result['steps'],[]);self.assertEqual(controller.verify(self.out)['status'],'needs_action_or_review')
        self.assertEqual([t['status'] for t in result['diagnosis']['tasks']],['fail','fail','pending'])

    def test_forged_chain_and_policy_change_rejected(self):
        result=self.run_controller();path=self.out/'recovery.json';original=path.read_bytes()
        forged=copy.deepcopy(result);forged['steps']=forged['steps'][:1];path.write_text(json.dumps(forged))
        with self.assertRaises(ValueError):controller.verify(self.out)
        path.write_bytes(original);self.data['max_steps']=1;self.policy.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):controller.verify(self.out)

    def test_invalid_task_or_unbounded_policy_rejects_before_output(self):
        for data in [dict(self.data,max_steps=21),dict(self.data,actions=[dict(task='review',catalogue='catalogue.json')]),dict(self.data,actions=self.data['actions']*2)]:
            self.policy.write_text(json.dumps(data))
            with self.assertRaises(ValueError):controller.run(self.plan,self.original,self.policy,self.out)
            self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()
