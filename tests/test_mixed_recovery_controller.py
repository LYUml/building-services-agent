import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa import recovery_controller as controller,workflow
from bsa.workflow_draft import draft
from bsa.cli import digest
from tests.test_pump import case

ROOT=Path(__file__).resolve().parents[1]

class MixedRecoveryTests(unittest.TestCase):
    def setUp(self):
        variable={'test_air_and_water_recover_in_one_preserved_source_graph':'BSA_MIXED_RECOVERY_TRIAL_OUT','test_unselected_fan_retains_failed_replay_and_stops_before_pump':'BSA_MIXED_NEGATIVE_TRIAL_OUT'}.get(self._testMethodName)
        saved=os.environ.get(variable) if variable else None
        if saved:
            self.root=Path(saved).resolve()
            if not self.root.is_relative_to(ROOT/'runs') or self.root.exists():raise ValueError('Fresh repository run required')
            self.root.mkdir(parents=True)
        else:
            temporary=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        shutil.copytree(ROOT/'examples/route-search',self.root,dirs_exist_ok=True)
        brief=self.root/'combined-brief.md'
        original=(self.root/'port-airflow-state-brief.md').read_text()
        brief.write_text(original.strip()+'\n\nCalculate an independent synthetic water-pump scenario using pump-network.json and weak-pump.json at the unchanged minimum flow. Keep it separate from the air-system installation; the combined recovery trial uses deliberately insufficient baseline catalogues, not real product data.\n',encoding='utf-8')
        scratch=self.root/'draft.json';draft(brief,scratch);generated=json.loads(scratch.read_text())
        source=json.loads((self.root/'port-airflow-state-plan.json').read_text());source.update(brief=brief.name,brief_sha256=digest(brief))
        extra=generated['requirements'][-1];extra.update(id='R-independent-pump',task='pump',acceptance=extra['quote'])
        source['requirements'].append(extra);source['passage_dispositions'][extra['passage']]='requirement'
        source['tasks'].insert(-1,dict(id='pump',kind='pump_operating_point',project='pump-network.json',curve='weak-pump.json'))
        source['tasks'][-1]['requires_pass'].append('pump')
        self.plan=self.root/'plan.json';self.plan.write_text(json.dumps(source))
        network,weak,_=case(1.2e-6);_,good,_=case()
        for name,value in [('pump-network.json',network),('weak-pump.json',weak)]: (self.root/name).write_text(json.dumps(value))
        pump=dict(objective='lowest declared preference among passing candidates',source='Independent synthetic water scenario',candidates=[dict(id='adequate-pump',source='Synthetic analytic curve',preference=0,curve=good)])
        (self.root/'pump-catalogue.json').write_text(json.dumps(pump))
        self.good=json.loads((self.root/'circular-fan-catalogue.json').read_text())
        weak_fan=copy.deepcopy(self.good);weak_fan['candidates']=weak_fan['candidates'][:2]
        (self.root/'circular-fan-catalogue.json').write_text(json.dumps(weak_fan))
        (self.root/'replacement-fans.json').write_text(json.dumps(self.good))
        self.data=dict(schema='bsa.recovery-policy/1',max_steps=4,actions=[dict(task='selection',catalogue='replacement-fans.json'),dict(task='pump',catalogue='pump-catalogue.json')])
        self.policy=self.root/'policy.json';self.out=self.root/'controller';self.original=self.root/'original'
        workflow.execute(self.plan,self.original)

    def run_controller(self):
        self.policy.write_text(json.dumps(self.data))
        return controller.run(self.plan,self.original,self.policy,self.out)

    def test_air_and_water_recover_in_one_preserved_source_graph(self):
        before=self.plan.read_bytes();baseline=(self.original/'workflow.json').read_bytes()
        result=self.run_controller();checked=controller.verify(self.out)
        self.assertEqual([r['task'] for r in result['steps']],['selection','pump'])
        self.assertEqual([r['selected'] for r in result['steps']],['supported','adequate-pump'])
        self.assertEqual(checked['steps'],2);self.assertFalse(checked['design_accepted'])
        self.assertEqual(result['diagnosis']['recovery_schedule']['ready_tasks'],['review'])
        self.assertTrue(all(t['status']=='pass' for t in result['diagnosis']['tasks'] if t['id']!='review'))
        self.assertEqual(self.plan.read_bytes(),before);self.assertEqual((self.original/'workflow.json').read_bytes(),baseline)
        self.assertEqual(json.loads(Path(result['final_plan']).read_text())['requirements'],json.loads(before)['requirements'])
        # First air replay must retain the unresolved independent water failure.
        first=json.loads((self.out/'step-1/workflow/workflow.json').read_text())
        self.assertEqual(first['tasks']['pump']['status'],'fail');self.assertEqual(first['tasks']['selection']['status'],'pass')

    def test_unselected_fan_retains_failed_replay_and_stops_before_pump(self):
        weak=copy.deepcopy(self.good);weak['candidates']=weak['candidates'][:2];weak['source']='Explicit revised synthetic no-feasible control'
        (self.root/'replacement-fans.json').write_text(json.dumps(weak))
        result=self.run_controller();self.assertEqual(result['status'],'no_feasible_candidate')
        self.assertEqual(controller.verify(self.out)['steps'],1);self.assertFalse((self.out/'step-2').exists())
        self.assertEqual(result['final_run'],str(self.out/'step-1/workflow'))
        self.assertEqual(next(t for t in result['diagnosis']['tasks'] if t['id']=='pump')['status'],'fail')
        self.assertIsNone(result['steps'][0]['selected'])

    def test_fan_cannot_claim_pump_electrical_eligibility(self):
        self.data['actions'][0]['electrical_task']='anything';self.policy.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ValueError,'Fan action'):controller.run(self.plan,self.original,self.policy,self.out)
        self.assertFalse(self.out.exists())

    def test_forged_cross_discipline_handoff_rejected(self):
        result=self.run_controller();path=self.out/'recovery.json'
        result['steps'][1]['input_run']=str(self.original);path.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError,'declared recovery action'):controller.verify(self.out)

if __name__=='__main__':unittest.main()
