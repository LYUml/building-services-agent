import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.modules import run,verify_result
from bsa.workflow_modules import inputs

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit pinned MOOSAS runtime required')
class MoosasProjectWorkspaceTests(unittest.TestCase):
    def test_external_native_recognition_rule_workflow_and_host_removal(self):
        # Temporary synthetic project outside tool source;no private coursework used.
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder).resolve()
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(project)}):
                source=runpy.run_path(str(ROOT/'examples/moosas-transform/build_ifc.py'))['build'](project/'native')
                plan=runpy.run_path(str(ROOT/'examples/moosas-transform/build_workflow.py'))['build'](project/'inputs',ifc_source=source,tolerances=dict(length_tolerance_m=1e-6,area_tolerance_m2=1e-8))
                official=plan.parent/'sources/emsd-bec-2024.pdf';official.write_bytes(b'SYNTHETIC RULE-SOURCE CONTROL ONLY')
                pack=plan.parent/'lighting-pack.json';data=json.loads(pack.read_text());data['sources']['emsd_bec_2024']['sha256']=digest(official);pack.write_text(json.dumps(data))
                runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps')
                output=project/'workflow';result=execute(plan,output,module_runtime=runtime)
                self.assertEqual(result['tasks']['recognition']['status'],'pass',result['tasks']['recognition'])
                self.assertEqual(result['tasks']['lighting-rules']['status'],'pass')
                self.assertEqual(result['tasks']['independent-electrical']['status'],'pass')
                self.assertTrue(verify(output)['integrity_pass']);context(plan,output)
                module=verify_result(output/'recognition/result.json')
                self.assertEqual(sorted(s['floor_area_m2'] for s in module['payload']['spaces']),[14,24,30])
                self.assertIn(str(ROOT/'src/bsa/workspace.py'),module['inputs'])
                self.assertTrue(all((output/p).is_relative_to(project) for p in result['artifact_hashes']))
                disabled=execute(plan,project/'disabled',module_runtime=runtime,disabled_module_providers=['moosas.ifc-room-recognition'])
                self.assertEqual(disabled['tasks']['recognition']['status'],'pending')
                self.assertEqual(disabled['tasks']['lighting-rules']['status'],'pending')
                self.assertEqual(disabled['tasks']['independent-electrical']['status'],'pass')
                context(plan,project/'disabled')
                with self.assertRaisesRegex(ValueError,'host-selected'):
                    inputs(project.parent/'unselected-request.json','moosas.ifc-room-recognition')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaises(ValueError):verify_result(output/'recognition/result.json')
                with self.assertRaises(ValueError):run(plan.parent/'native-request.json','moosas.ifc-room-recognition',project/'denied')
                self.assertFalse((project/'denied').exists())
