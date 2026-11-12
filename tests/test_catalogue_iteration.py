import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.catalogue_iteration import baseline_signature,revised_plan,run,SCOPE
from bsa.catalogue_iteration_verify import verify
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class CatalogueIterationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.plan=self.root/'original.json'
        self.plan.write_text('{}');self.catalogue=self.root/'catalogue.json';self.catalogue.write_text('{}')
        self.original=self.root/'original-run';self.original.mkdir()
        self.target=self.root/'recovered.json';self.out=self.root/'iteration'

    def invoke(self,**options):
        return run(self.plan,self.original,'selection',self.catalogue,self.target,self.out,**options)

    def test_revision_changes_only_explicit_catalogue_not_requirements_or_targets(self):
        source=json.loads((ROOT/'examples/route-search/port-airflow-state-plan.json').read_text())
        original=copy.deepcopy(source)
        revised=revised_plan(source,'selection',self.catalogue,self.target)
        expected=copy.deepcopy(source)
        next(t for t in expected['tasks'] if t['id']=='selection')['catalogue']='catalogue.json'
        self.assertEqual(revised,expected);self.assertEqual(source,original)
        self.assertEqual(len(revised['requirements']),10)
        self.assertEqual(revised['requirements'],source['requirements'])

    def test_external_catalogue_and_existing_outputs_reject_before_writes(self):
        with self.assertRaisesRegex(ValueError,'inside the plan'):
            run(self.plan,self.original,'selection',ROOT/'examples/route-search/circular-fan-catalogue.json',self.target,self.out)
        self.assertFalse(self.out.exists());self.assertFalse(self.target.exists())
        self.out.mkdir()
        with self.assertRaisesRegex(ValueError,'Fresh'):self.invoke()

    def test_untrusted_options_never_become_document_commands(self):
        with self.assertRaisesRegex(ValueError,'host runtime'):
            self.invoke(execute_options={'command':'execute arbitrary document content'})
        self.assertFalse(self.out.exists())

    def test_stale_original_cannot_start_recovery(self):
        with patch('bsa.catalogue_iteration.delivery.context',return_value=({}, {}, {'integrity_pass':False})),patch('bsa.catalogue_iteration.circular_fan_selection.run') as solve:
            with self.assertRaisesRegex(ValueError,'stale'):self.invoke()
        solve.assert_not_called();self.assertFalse(self.out.exists());self.assertFalse(self.target.exists())

    def test_blocked_selection_cannot_skip_upstream_recovery(self):
        source={'tasks':[{'id':'selection','kind':'circular_fan_selection'}]}
        report={'tasks':{'selection':{'status':'fail'}}}
        with patch('bsa.catalogue_iteration.delivery.context',return_value=(source,report,{'integrity_pass':True})),patch('bsa.catalogue_iteration.workflow_status.diagnose',return_value={'recovery_schedule':{'ready_tasks':['pressure']}}),patch('bsa.catalogue_iteration.circular_fan_selection.run') as solve:
            with self.assertRaisesRegex(ValueError,'Ready failed'):self.invoke()
        solve.assert_not_called();self.assertFalse(self.out.exists())

    def test_baseline_signature_retains_failures_and_native_operating_results(self):
        record={'candidates':[{'id':'weak','preference':0,'status':'fail',
            'calculated_checks_pass':False,'checks':{'minimum_flow':False},
            'operating_point':{'flow_m3_s':.06},'report_sha256':'location-dependent'}]}
        second=copy.deepcopy(record);second['candidates'][0]['report_sha256']='other'
        self.assertEqual(baseline_signature(record),baseline_signature(second))
        second['candidates'][0]['checks']['minimum_flow']=True
        self.assertNotEqual(baseline_signature(record),baseline_signature(second))

    def test_changed_baseline_result_stops_before_new_plan_and_execution(self):
        old_catalogue=self.root/'old-catalogue.json';old_catalogue.write_text('{"old":true}')
        baseline={'selected':None,'calculated_checks_pass':False,'candidates':[
            {'id':'weak','preference':0,'status':'fail','calculated_checks_pass':False,
             'checks':{'minimum_flow':False},'operating_point':{'flow_m3_s':.06}}]}
        (self.original/'selection').mkdir();saved=self.original/'selection/fan-selection.json'
        saved.write_text(json.dumps(baseline));(self.original/'workflow.json').write_text('{}')
        source={'tasks':[{'id':'selection','kind':'circular_fan_selection','depends_on':'pressure','catalogue':'old-catalogue.json'}], 'requirements':[{'id':'R1'}]}
        report={'tasks':{'selection':{'status':'fail'}},'inputs':{},'artifact_hashes':{'selection/fan-selection.json':digest(saved)}}
        changed=copy.deepcopy(baseline);changed['candidates'][0]['operating_point']['flow_m3_s']=.07
        with patch('bsa.catalogue_iteration.delivery.context',return_value=(source,report,{'integrity_pass':True})),patch('bsa.catalogue_iteration.workflow_status.diagnose',return_value={'recovery_schedule':{'ready_tasks':['selection']}}),patch('bsa.catalogue_iteration.circular_fan_selection.context',return_value=(None,None,{},None,None,None)),patch('bsa.catalogue_iteration.circular_fan_selection.run',return_value=changed),patch('bsa.catalogue_iteration.workflow.execute') as execute:
            result=self.invoke()
        self.assertEqual(result['status'],'failed');self.assertIn('baseline',result['stage_errors'])
        self.assertFalse(self.target.exists());execute.assert_not_called()

    def test_verifier_rejects_changed_sources_and_unlisted_artifacts(self):
        self.out.mkdir()
        receipt={'schema':'bsa.catalogue-iteration/1','scope':SCOPE,'design_accepted':False,
            'original_inputs_unchanged':True,'inputs':{str(self.plan):digest(self.plan)},'artifacts':{}}
        path=self.out/'iteration.json';path.write_text(json.dumps(receipt))
        self.plan.write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError,'source or method changed'):verify(self.out)
        receipt['inputs'][str(self.plan)]=digest(self.plan);path.write_text(json.dumps(receipt))
        (self.out/'unlisted.txt').write_text('not inventoried')
        with self.assertRaisesRegex(ValueError,'artifact inventory changed'):verify(self.out)


if __name__=='__main__':unittest.main()
