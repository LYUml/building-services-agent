import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from bsa.changes import core
from bsa.module_contract import read_json
from bsa import modules
from bsa.source_refs import file_hash,reference
from bsa.workflow import execute,verify
from tests import test_changes


class SelectiveWorkflowTests(unittest.TestCase):
    def setUp(self):
        fixture=test_changes.ChangeImpactTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.fixture=fixture
        self.root=fixture.root;self.plan=fixture.plan;self.checkpoint=fixture.checkpoint

    def test_changed_branch_runs_once_and_unchanged_branch_reaches_common_report(self):
        self.fixture.change_primary()
        with patch('bsa.modules.run',wraps=modules.run) as producer:
            result=execute(self.plan,self.root/'selective',reuse_checkpoint=self.checkpoint)
        self.assertEqual(producer.call_count,1)
        self.assertEqual(result['reuse']['reused_tasks'],['independent'])
        self.assertEqual(result['tasks']['analysis']['status'],'pass')
        self.assertEqual(result['tasks']['data']['status'],'pass')
        self.assertEqual(result['tasks']['review']['status'],'pending')
        self.assertEqual({r['id'] for r in result['requirements']},{r['id'] for r in self.fixture.data['requirements']})
        self.assertTrue(all(r['acceptance_status']=='pending review' for r in result['requirements']))
        self.assertTrue(verify(self.root/'selective')['integrity_pass'])
        self.assertTrue(core.verify_reuse(self.root/'selective/_reuse/independent')['integrity_pass'])
        from bsa.delivery import context
        context(self.plan,self.root/'selective')

    def test_disabled_provider_preserves_pending_and_does_not_reuse(self):
        result=execute(self.plan,self.root/'disabled',reuse_checkpoint=self.checkpoint,
                       disabled_module_providers=['bsa.single-phase-circuits'])
        self.assertEqual(result['reuse']['reused_tasks'],[])
        self.assertEqual(result['tasks']['analysis']['status'],'pending')
        self.assertEqual(result['tasks']['data']['status'],'pending')
        self.assertTrue(verify(self.root/'disabled')['integrity_pass'])

    def test_lost_reuse_metadata_and_missing_checkpoint_pin_are_rejected(self):
        out=self.root/'run';execute(self.plan,out,reuse_checkpoint=self.checkpoint)
        original=read_json(out/'workflow.json')
        for mode in ('record','pin'):
            report=copy.deepcopy(original)
            if mode=='record':del report['reuse']
            else:del report['inputs'][str(self.checkpoint/'receipt.json')]
            self.fixture.save(out/'workflow.json',report)
            self.assertFalse(verify(out)['integrity_pass'])

    def test_foreign_canonical_copy_cannot_replace_declared_reuse_binding(self):
        out=self.root/'run';execute(self.plan,out,reuse_checkpoint=self.checkpoint)
        core.reuse(self.checkpoint,'independent',self.root/'foreign',module_out=self.root/'foreign-module')
        path=out/'_reuse/independent/receipt.json';data=read_json(path)
        data['module_result']=reference(self.root/'foreign-module/result.json');self.fixture.save(path,data)
        self.assertTrue(core.verify_reuse(path.parent)['integrity_pass'])
        report=read_json(out/'workflow.json');report['artifact_hashes']['_reuse/independent/receipt.json']=file_hash(path)
        self.fixture.save(out/'workflow.json',report)
        self.assertFalse(verify(out)['integrity_pass'])

    def test_explicit_runtime_disables_reuse_but_empty_cli_defaults_do_not(self):
        result=execute(self.plan,self.root/'cli-defaults',reuse_checkpoint=self.checkpoint,
                       module_runtime={'upstream':None,'deps':None})
        self.assertEqual(set(result['reuse']['reused_tasks']),{'analysis','independent'})
        with patch('bsa.modules.run',wraps=modules.run) as producer:
            result=execute(self.plan,self.root/'runtime',reuse_checkpoint=self.checkpoint,
                           module_runtime={'python':Path(sys.executable)})
        self.assertEqual(producer.call_count,2)
        self.assertEqual(result['reuse']['reused_tasks'],[])

    def test_linked_canonical_task_is_rejected_even_with_coherent_binding(self):
        out=self.root/'run';execute(self.plan,out,reuse_checkpoint=self.checkpoint)
        target=out/'independent';saved=self.root/'saved-copy'
        self.assertTrue(target.resolve().is_relative_to(self.root))
        self.assertTrue(saved.resolve().is_relative_to(self.root))
        target.rename(saved)
        try:os.symlink(saved,target,target_is_directory=True)
        except OSError:
            if os.name!='nt':raise
            import _winapi
            _winapi.CreateJunction(str(saved),str(target))
        path=out/'_reuse/independent/receipt.json';data=read_json(path)
        data['module_result']=reference(saved/'result.json');self.fixture.save(path,data)
        report=read_json(out/'workflow.json');report['artifact_hashes']['_reuse/independent/receipt.json']=file_hash(path)
        self.fixture.save(out/'workflow.json',report)
        self.assertFalse(verify(out)['integrity_pass'])
