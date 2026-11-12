import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from bsa import hvac_project,hvac_refresh
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class HVACRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.plan=runpy.run_path(str(ROOT/'examples/hvac-package/build_inputs.py'))['build'](self.root/'inputs')
        self.original=self.root/'original.json';self.target=self.root/'fresh.json';self.out=self.root/'refresh'
        hvac_project.create(self.plan,self.original,terminal_review=self.plan.parent/'review.json',junction_review_native_task='native',system_paths_native_task='native')

    def stale_method(self):
        data=json.loads(self.original.read_text());name=next(key for key in data['input_hashes'] if key.endswith('src/bsa/workflow.py'))
        data['input_hashes'][name]='0'*64;self.original.write_text(json.dumps(data))

    def test_tool_only_drift_creates_fresh_inventory_and_preserves_original_settings(self):
        self.stale_method();before=self.original.read_bytes();plan_before=self.plan.read_bytes()
        drift=hvac_refresh.inspect(self.original)
        self.assertTrue(drift['source_unchanged']);self.assertEqual(len(drift['tool_drift']['changed']),1)
        with self.assertRaisesRegex(ValueError,'source changed'):hvac_project.load(self.original)
        result=hvac_refresh.run(self.original,self.target,self.out)
        self.assertEqual(result['status'],'prepared');self.assertFalse(result['design_accepted'])
        verified=hvac_refresh.verify(self.out)
        self.assertTrue(verified['project_sources_unchanged']);self.assertFalse(verified['engineering_executed'])
        files,selectors,_=hvac_project.load(self.target)
        self.assertEqual(files['plan'],self.plan)
        self.assertEqual(files['terminal_review'],self.plan.parent/'review.json')
        self.assertEqual(selectors['system_paths_native_task'],'native')
        self.assertEqual(self.original.read_bytes(),before);self.assertEqual(self.plan.read_bytes(),plan_before)

    def test_project_data_drift_cannot_be_reclassified_as_tool_upgrade(self):
        self.stale_method();path=self.plan.parent/'source.dxf';path.write_bytes(path.read_bytes()+b'\n')
        self.assertFalse(hvac_refresh.inspect(self.original)['source_unchanged'])
        with patch('bsa.hvac_refresh.modules.run') as inventory:
            with self.assertRaisesRegex(ValueError,'Project data changed'):hvac_refresh.run(self.original,self.target,self.out)
        inventory.assert_not_called();self.assertFalse(self.out.exists());self.assertFalse(self.target.exists())

    def test_new_tool_files_are_visible_and_review_fields_cannot_run_commands(self):
        data=json.loads(self.original.read_text());name=next(key for key in data['input_hashes'] if key.endswith('src/bsa/hvac_refresh.py'))
        data['input_hashes'].pop(name);self.original.write_text(json.dumps(data))
        self.assertIn(str(ROOT/'src/bsa/hvac_refresh.py'),hvac_refresh.inspect(self.original)['tool_drift']['added'])
        data['command']='untrusted document command';self.original.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Exact HVAC'):hvac_refresh.run(self.original,self.target,self.out)
        self.assertFalse(self.out.exists())

    def test_refresh_artifact_and_target_tampering_reject(self):
        hvac_refresh.run(self.original,self.target,self.out)
        data=self.target.read_bytes();self.target.write_bytes(data+b' ')
        with self.assertRaisesRegex(ValueError,'configuration changed'):hvac_refresh.verify(self.out)
        self.target.write_bytes(data);(self.out/'requirements-request.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'artifacts changed'):hvac_refresh.verify(self.out)

    def test_existing_inventory_is_preserved_and_cannot_contain_new_outputs(self):
        hvac_refresh.run(self.original,self.target,self.out)
        previous=(self.out/'requirements/result.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'outside the original requirements'):
            hvac_refresh.run(self.target,self.root/'another.json',self.out/'requirements/nested-refresh')
        self.assertEqual((self.out/'requirements/result.json').read_bytes(),previous)

    def test_unavailable_inventory_never_creates_a_replay_configuration(self):
        before=self.original.read_bytes()
        with patch('bsa.hvac_refresh.modules.run',return_value={'execution':{'status':'unavailable'}}):
            result=hvac_refresh.run(self.original,self.target,self.out)
        self.assertEqual(result['status'],'requirements_unavailable')
        self.assertFalse(self.target.exists());self.assertEqual(self.original.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'Complete unaccepted'):hvac_refresh.verify(self.out)

    def test_data_change_during_preparation_blocks_new_configuration(self):
        source=self.plan.parent/'source.dxf'
        def mutate(*args,**kwargs):
            source.write_bytes(source.read_bytes()+b'\n')
            return {'execution':{'status':'completed'}}
        with patch('bsa.hvac_refresh.modules.run',side_effect=mutate):
            result=hvac_refresh.run(self.original,self.target,self.out)
        self.assertEqual(result['status'],'source_changed');self.assertFalse(self.target.exists())
        self.assertIn('requirements',result['stage_errors'])

    def test_unselected_external_workspace_cannot_be_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(root)}):
                plan=runpy.run_path(str(ROOT/'examples/hvac-package/build_inputs.py'))['build'](root/'inputs')
                hvac_project.create(plan,root/'original.json')
                result=hvac_refresh.run(root/'original.json',root/'fresh.json',root/'refresh')
                self.assertEqual(result['status'],'prepared');self.assertTrue(hvac_refresh.verify(root/'refresh')['integrity_pass'])
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaisesRegex(ValueError,'host-selected'):hvac_refresh.inspect(root/'original.json')


if __name__=='__main__':unittest.main()
