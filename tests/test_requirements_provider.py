import copy,json,os,runpy,tempfile,unittest
from pathlib import Path
from bsa.cli import digest
from bsa.project_start import start
from bsa.modules import run,verify_result
from bsa.module_contract import validate
ROOT=Path(__file__).resolve().parents[1]

class RequirementsProviderTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  brief=self.root/'brief.md';brief.write_text('Calculate ventilation.\n\nProduce an editable drawing.');reference=self.root/'reference.md';reference.write_text('Example practice;reference context only.')
  r=start(brief,self.root/'intake',references=[reference]);self.plan=self.root/'intake'/r['effective_plan']
  self.request=self.root/'request.json';request=dict(schema='bsa.module-request/1',project_id='requirements-control',scenario_id='source-only',capability='requirements.source-inventory',coordinate_frame=dict(id='no-geometry-claim',kind='source-world-si',length_unit='m',georeferenced=False),sources=dict(plan=dict(path=os.path.relpath(self.plan,self.root),sha256=digest(self.plan))))
  self.request.write_text(json.dumps(request))
 def test_complete_source_coverage_and_pending_interpretation_preserved(self):
  r=run(self.request,'bsa.source-requirements',self.root/'output');verify_result(self.root/'output/result.json')
  p=r['payload'];self.assertEqual(len(p['passages']),3);self.assertEqual(len(p['requirements']),2);self.assertEqual(len(p['unresolved_inputs']),2)
  self.assertEqual(p['passages'][-1]['disposition'],'context');self.assertEqual(p['engineering_execution'],'not_executed');self.assertEqual(p['interpretation_status'],'not_assessed')
 def test_schema_valid_acceptance_and_pending_input_mutation_reject(self):
  r=run(self.request,'bsa.source-requirements',self.root/'output');path=self.root/'output/result.json'
  for kind in ['acceptance','input','context']:
   altered=copy.deepcopy(r)
   if kind=='acceptance':altered['payload']['requirements'][0]['acceptance']='Claim completed'
   elif kind=='input':altered['payload']['unresolved_inputs']=[]
   else:altered['payload']['passages'][-1]['text']='Replacement reference text'
   validate(altered);path.write_text(json.dumps(altered))
   with self.assertRaisesRegex(ValueError,'complete source replay'):verify_result(path)
 def test_disable_and_changed_source(self):
  r=run(self.request,'bsa.source-requirements',self.root/'disabled',disabled=True);self.assertIsNone(r['payload']);verify_result(self.root/'disabled/result.json')
  run(self.request,'bsa.source-requirements',self.root/'output')
  brief=next((self.root/'intake/sources/D001').iterdir());brief.write_text('Changed source')
  with self.assertRaises(ValueError):verify_result(self.root/'output/result.json')
 def test_omitted_passage_and_false_engineering_state_reject_contract(self):
  p=run(self.request,'bsa.source-requirements',self.root/'output')['payload'];p['passages']=p['passages'][1:]
  with self.assertRaises(ValueError):validate(p)

  p['engineering_execution']='completed'
  with self.assertRaises(ValueError):validate(p)

 def test_bound_workflow_keeps_blockers_and_rejects_rewritten_matrix(self):
  from bsa.workflow import execute,verify
  from bsa.delivery import context
  run(self.request,'bsa.source-requirements',self.root/'inventory')
  result=self.root/'inventory/result.json';out=self.root/'workflow'
  r=execute(self.plan,out,requirements_result=result)
  self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
  self.assertTrue(all(t['status']=='pending' for t in r['tasks'].values()))
  self.assertEqual(r['unresolved_inputs'],json.loads(self.plan.read_text())['unresolved_inputs'])
  clean=copy.deepcopy(r)
  r['requirements'][0]['acceptance']='Invented completed requirement'
  (out/'workflow.json').write_text(json.dumps(r))
  self.assertFalse(verify(out)['integrity_pass'])
  with self.assertRaisesRegex(ValueError,'matrix differs'):context(self.plan,out)
  clean.pop('requirements_inventory');(out/'workflow.json').write_text(json.dumps(clean))
  self.assertFalse(verify(out)['integrity_pass'])

 def test_binding_rejects_same_bytes_other_plan_and_disabled_inventory(self):
  from bsa.workflow import execute
  run(self.request,'bsa.source-requirements',self.root/'inventory')
  clone=self.plan.parent/'clone.json';clone.write_bytes(self.plan.read_bytes())
  with self.assertRaisesRegex(ValueError,'exact execution plan'):
   execute(clone,self.root/'other',requirements_result=self.root/'inventory/result.json')
  self.assertFalse((self.root/'other').exists())
  run(self.request,'bsa.source-requirements',self.root/'disabled',disabled=True)
  with self.assertRaisesRegex(ValueError,'Completed verified requirements'):
   execute(self.plan,self.root/'no-result',requirements_result=self.root/'disabled/result.json')
  self.assertFalse((self.root/'no-result').exists())
