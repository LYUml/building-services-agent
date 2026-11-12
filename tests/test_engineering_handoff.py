import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest

from bsa.engineering_handoff import GENERIC,materialize,verify,run

ROOT=Path(__file__).resolve().parents[1]


class EngineeringHandoffTests(unittest.TestCase):
    def sample(self):
        source=dict(tasks=[dict(id='interpret-1',kind='manual'),dict(id='interpret-2',kind='manual',requires_pass=['interpret-1'])],
            passage_dispositions={'P1':'requirement','P2':'requirement'},
            requirements=[dict(id='R1',task='interpret-1',passage='P1',quote='Given electrical inputs',acceptance='Original obligation'),dict(id='R2',task='interpret-2',passage='P2',quote='Review physical routing',acceptance='Original physical review')],
            unresolved_inputs=[dict(id='interpretation-1',kind='missing',description=GENERIC,sources=[dict(passage='P1',quote='Given electrical inputs')],blocks_tasks=['interpret-1']),
                dict(id='actual-route',kind='missing',description='Actual surveyed route is missing',sources=[dict(passage='P2',quote='Review physical routing')],blocks_tasks=['interpret-2'])])
        record=dict(schema='bsa.engineering-handoff/1',source_plan_sha256='not-a-live-plan',tasks=[dict(id='electrical',kind='electrical',project='electrical.json'),dict(id='review',kind='manual')],
            requirement_bindings={'R1':dict(tasks=['electrical'],acceptance='Conditional electrical checks'), 'R2':dict(tasks=['review'],acceptance='Review actual physical routing')},
            interpretation_notes={'interpretation-1':'Source specifies explicitly synthetic electrical data; physical routing is still missing.'},extra_unresolved_inputs=[])
        return source,record

    def test_real_gaps_dependencies_quotes_and_original_acceptance_survive(self):
        source,record=self.sample();before=copy.deepcopy(source);result=materialize(source,record)
        self.assertEqual(source,before)
        self.assertEqual(result['tasks'][1]['requires_pass'],['electrical'])
        gap=result['unresolved_inputs'][0]
        self.assertEqual(gap,dict(source['unresolved_inputs'][1],blocks_tasks=['review']))
        self.assertEqual(result['passage_dispositions'],source['passage_dispositions'])
        for old,new in zip(source['requirements'],result['requirements']):
            self.assertEqual(new['quote'],old['quote']);self.assertEqual(new['original_requirement_id'],old['id'])
            self.assertEqual(new['original_acceptance'],old['acceptance'])

    def test_missing_mapping_empty_notes_unknown_tasks_and_collapsed_dependency_reject(self):
        source,record=self.sample()
        for mode in ('missing','notes','unknown','collapse','unreferenced'):
            row=copy.deepcopy(record)
            if mode=='missing':row['requirement_bindings'].pop('R2')
            if mode=='notes':row['interpretation_notes']={}
            if mode=='unknown':row['requirement_bindings']['R1']['tasks']=['missing']
            if mode=='collapse':row['requirement_bindings']['R2']['tasks']=['electrical'];row['tasks'].pop()
            if mode=='unreferenced':row['tasks'].append(dict(id='unrelated',kind='manual'))
            with self.subTest(mode=mode),self.assertRaises(ValueError):materialize(source,row)

    def test_existing_engineering_plan_cannot_be_overwritten(self):
        source,record=self.sample();source['tasks'][0]['kind']='electrical'
        with self.assertRaisesRegex(ValueError,'cannot be replaced'):materialize(source,record)

    def actual(self,missing):
        temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(temp.cleanup)
        root=Path(temp.name)/'project'
        demo=runpy.run_path(str(ROOT/'scripts/run_engineering_handoff_demo.py'))
        summary=demo['execute'](root,missing)
        self.assertEqual(summary['stage_errors'],{})
        verified=verify(root/'engineering-run')
        self.assertEqual(len(verified['original_requirement_ids']),5)
        self.assertFalse(verified['design_accepted'])
        return root,verified

    def test_actual_cross_discipline_execution_and_receipt_tamper(self):
        root,result=self.actual(False)
        self.assertEqual(result['task_statuses'],dict(electrical='pass',air='pass',water='pass',envelopes='pass',review='pending'))
        self.assertEqual(result['retained_input_gaps'],[])
        path=root/'engineering-run/handoff.json';original=path.read_bytes();record=json.loads(original)
        try:
            record['handoff']['original_requirements']=0;path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'original requirements or gaps'):verify(root/'engineering-run')
        finally:path.write_bytes(original)
        project=root/'electrical.json';before=project.read_bytes()
        try:
            changed=json.loads(before);changed['devices'][0]['electrical_kw']=40
            project.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'source or method changed'):verify(root/'engineering-run')
        finally:project.write_bytes(before)
        self.assertTrue(verify(root/'engineering-run')['integrity_pass'])

    def test_actual_missing_water_input_keeps_independent_work_and_blocks_review(self):
        root,result=self.actual(True)
        self.assertEqual(result['task_statuses'],dict(electrical='pass',air='pass',water='pending',envelopes='pass',review='pending'))
        self.assertEqual(result['retained_input_gaps'][0]['id'],'water-property-review')
        self.assertFalse((root/'engineering-run/workflow/water').exists())
        self.assertEqual(result['recovery_schedule']['ready_tasks'],['water'])

    def test_disabled_requirement_provider_prevents_all_engine_execution(self):
        root,_=self.actual(False)
        result=run(root/'plan.json',root/'engineering-review.json',root/'disabled-plan.json',root/'disabled-run',execute_options={'disabled_module_providers':['bsa.source-requirements']})
        self.assertEqual(result['status'],'requirements_unavailable')
        self.assertNotIn('workflow',result['stages'])
        self.assertFalse((root/'disabled-run/workflow').exists())


if __name__=='__main__':unittest.main()
