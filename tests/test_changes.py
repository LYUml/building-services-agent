import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from bsa.changes import core
from bsa.engineering_data.module_bridge import export
from bsa.module_contract import read_json
from bsa.modules import run, verify_result
from bsa.source_refs import file_hash
from bsa.workflow import execute
from tests import test_engineering_data_workflow


class ChangeImpactTests(unittest.TestCase):
    def setUp(self):
        fixture=test_engineering_data_workflow.CommonDataWorkflowTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture=fixture;self.root=fixture.root;self.save=fixture.save
        self.plan=fixture.plan;self.data=fixture.plan_data
        (self.root/'independent.json').write_bytes(fixture.project.read_bytes())
        self.request=copy.deepcopy(fixture.request_data)
        self.request['sources']['project']=dict(path='independent.json',sha256=file_hash(self.root/'independent.json'))
        self.save(self.root/'independent-request.json',self.request)
        self.data['tasks'].insert(1,dict(id='independent',kind='module_analysis',request='independent-request.json',provider='bsa.single-phase-circuits'))
        requirement=copy.deepcopy(self.data['requirements'][0]);requirement.update(id='R-independent',task='independent')
        self.data['requirements'].append(requirement);self.save(self.plan,self.data)
        self.baseline=self.root/'baseline';execute(self.plan,self.baseline)
        self.checkpoint=self.root/'checkpoint';core.checkpoint(self.baseline,self.checkpoint)

    def change_primary(self):
        project=read_json(self.fixture.project)
        for row in project['devices']:row['electrical_kw']*=1.25
        self.save(self.fixture.project,project)
        self.fixture.request_data['sources']['project']['sha256']=file_hash(self.fixture.project)
        self.save(self.fixture.request,self.fixture.request_data)

    def test_primary_change_invalidates_descendants_and_preserves_independent_branch(self):
        self.change_primary();result=core.impact(self.checkpoint)
        self.assertTrue(result['plan_valid'])
        self.assertTrue(result['tasks']['analysis']['invalidated'])
        self.assertTrue(result['tasks']['data']['invalidated'])
        self.assertTrue(result['tasks']['review']['invalidated'])
        self.assertTrue(result['tasks']['independent']['reuse_eligible'])
        self.assertFalse(result['design_accepted'])
        with self.assertRaises(ValueError):core.reuse(self.checkpoint,'analysis',self.root/'denied')
        self.assertFalse((self.root/'denied').exists())

    def test_reuse_passes_original_verifier_and_common_report_without_running_solver(self):
        self.change_primary()
        with patch('bsa.modules.run',side_effect=AssertionError('Unchanged branch must not recalculate')):
            core.reuse(self.checkpoint,'independent',self.root/'reused')
        self.assertTrue(core.verify_reuse(self.root/'reused')['integrity_pass'])
        old=verify_result(self.baseline/'independent/result.json')
        new=verify_result(self.root/'reused/module/result.json')
        self.assertEqual(new,old)
        export(self.root/'reused/module/result.json',self.root/'report')
        self.assertTrue((self.root/'report/summary.html').is_file())
        self.assertFalse(read_json(self.root/'report/model.json')['design_accepted'])

    def test_changed_branch_recalculates_actual_current_and_report_by_25_percent(self):
        before=verify_result(self.baseline/'analysis/result.json')['payload']['circuits'][0]['design_current_a']
        self.change_primary()
        after=run(self.fixture.request,'bsa.single-phase-circuits',self.root/'fresh')
        self.assertAlmostEqual(after['payload']['circuits'][0]['design_current_a'],before*1.25)
        export(self.root/'fresh/result.json',self.root/'fresh-report')
        model=read_json(self.root/'fresh-report/model.json')
        circuit=next(e for e in model['entities'] if e['kind']=='electrical_circuit')
        self.assertAlmostEqual(circuit['quantities']['design_current_a']['value'],before*1.25)

    def test_recipe_change_is_local_but_brief_or_context_change_is_global(self):
        self.data['tasks'][0]['description']='Changed calculation intent'
        self.save(self.plan,self.data)
        result=core.impact(self.checkpoint)
        self.assertIn('task_recipe_changed',result['tasks']['analysis']['reasons'])
        self.assertTrue(result['tasks']['independent']['reuse_eligible'])
        context=read_json(self.root/'context.json');context['scenario_id']='different-scenario'
        self.save(self.root/'context.json',context)
        self.assertFalse(core.impact(self.checkpoint)['tasks']['independent']['reuse_eligible'])

    def test_artifact_change_and_unknown_artifact_invalidate_reuse(self):
        extra=self.baseline/'independent/extra.txt';extra.write_text('Unaccounted file',encoding='utf-8')
        result=core.impact(self.checkpoint)
        self.assertIn('artifact_changed',result['tasks']['independent']['reasons'])
        with self.assertRaises(ValueError):core.reuse(self.checkpoint,'independent',self.root/'denied')

    def test_rehashed_archive_cannot_change_original_module_evidence(self):
        path=self.checkpoint/'module-independent.json';data=read_json(path)
        data['project_id']='forged';self.save(path,data)
        receipt=read_json(self.checkpoint/'receipt.json');receipt['artifacts'][path.name]=file_hash(path)
        self.save(self.checkpoint/'receipt.json',receipt)
        with self.assertRaisesRegex(ValueError,'original workflow artifact'):core.impact(self.checkpoint)

    def test_method_drift_and_detector_drift_block_unsafe_reuse(self):
        result=verify_result(self.baseline/'independent/result.json')
        method=next(Path(p) for p in result['inputs'] if '/src/' in Path(p).as_posix())
        actual=core.file_hash
        def changed(path):return '0'*64 if Path(path)==method else actual(path)
        with patch('bsa.changes.core.file_hash',side_effect=changed):
            assessed=core.impact(self.checkpoint)
            self.assertTrue(any(r['kind']=='method_or_contract' for r in assessed['changes']))
            self.assertFalse(assessed['tasks']['independent']['reuse_eligible'])
        with patch('bsa.changes.core.methods',return_value={}):
            self.assertIn('change_detector_method_changed',core.impact(self.checkpoint)['tasks']['independent']['reasons'])

    def test_reuse_bytes_cannot_be_rewritten_with_outer_hashes(self):
        core.reuse(self.checkpoint,'independent',self.root/'reuse')
        target=self.root/'reuse/module/result.json';data=read_json(target)
        data['acceptance']['scope']='Invented acceptance';self.save(target,data)
        receipt=read_json(self.root/'reuse/receipt.json');receipt['artifacts']['module/result.json']=file_hash(target)
        self.save(self.root/'reuse/receipt.json',receipt)
        with self.assertRaises(ValueError):core.verify_reuse(self.root/'reuse')

    def test_root_cli_builds_and_reads_checkpoint(self):
        command=[sys.executable,'-X','utf8','-m','bsa.cli','changes']
        built=subprocess.run(command+['checkpoint',str(self.baseline),'--out',str(self.root/'cli-checkpoint')],capture_output=True,text=True)
        self.assertEqual(built.returncode,0,built.stderr)
        checked=subprocess.run(command+['analyze',str(self.root/'cli-checkpoint')],capture_output=True,text=True)
        self.assertEqual(checked.returncode,0,checked.stderr)
        self.assertTrue(json.loads(checked.stdout)['tasks']['analysis']['reuse_eligible'])

    def test_valid_numerical_module_from_another_project_cannot_join_checkpoint(self):
        self.request['project_id']='25b352e5-6b6d-4722-b38e-8ccf606e529d'
        self.save(self.root/'independent-request.json',self.request)
        execute(self.plan,self.root/'mixed')
        with self.assertRaisesRegex(ValueError,'declared project/scenario'):
            core.checkpoint(self.root/'mixed',self.root/'mixed-checkpoint')
        self.assertFalse((self.root/'mixed-checkpoint').exists())

    def test_malformed_current_plan_is_reported_and_never_reused(self):
        self.plan.write_text('{invalid current plan',encoding='utf-8')
        result=core.impact(self.checkpoint)
        self.assertFalse(result['plan_valid'])
        self.assertTrue(all(not row['reuse_eligible'] for row in result['tasks'].values()))

    def test_environment_drift_and_unverified_provider_paths_never_reuse(self):
        with patch('bsa.changes.core.environment',return_value={'ready':False}):
            result=core.impact(self.checkpoint)
            self.assertTrue(result['upstream_environment']['changed'])
            self.assertIn('upstream_environment_changed',result['tasks']['independent']['reasons'])
        with patch('bsa.changes.core.REUSABLE_PROVIDERS',set()):
            self.assertFalse(core.impact(self.checkpoint)['tasks']['independent']['reuse_eligible'])
