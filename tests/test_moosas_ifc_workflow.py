import copy
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.modules import verify_result

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit pinned MOOSAS runtime required')
class MoosasIfcWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        source=runpy.run_path(str(ROOT/'examples/moosas-transform/build_ifc.py'))['build'](self.root/'source')
        self.plan=runpy.run_path(str(ROOT/'examples/moosas-transform/build_workflow.py'))['build'](self.root/'inputs',ifc_source=source,tolerances=dict(length_tolerance_m=1e-6,area_tolerance_m2=1e-8))
        self.runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps')
        # Unit rule-source control only;retained actual trials use pinned official bytes.
        pdf=self.plan.parent/'sources/emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC RULE-SOURCE CONTROL')
        pack=self.plan.parent/'lighting-pack.json';data=json.loads(pack.read_text());data['sources']['emsd_bec_2024']['sha256']=digest(pdf);pack.write_text(json.dumps(data))

    def execute(self,name,runtime=None,**kwargs):
        out=self.root/name;r=execute(self.plan,out,module_runtime=self.runtime if runtime is None else runtime,**kwargs)
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        return r,out

    def test_saved_ifc_complete_geometry_and_rule_inheritance(self):
        r,out=self.execute('enabled')
        self.assertEqual({k:v['status'] for k,v in r['tasks'].items()},{'recognition':'pass','lighting-rules':'pass','review':'pending','independent-electrical':'pass'})
        module=verify_result(out/'recognition/result.json')
        spaces=module['payload']['spaces'];self.assertEqual(sorted(s['floor_area_m2'] for s in spaces),[14,24,30])
        bound=json.loads((out/'lighting-rules/bound-space-projects.json').read_text())
        self.assertEqual({s['id']:s['floor_area_m2'] for s in spaces},{k:v['lighting_space']['internal_floor_area']['value'] for k,v in bound.items()})
        self.assertIn(str((self.plan.parent/'native-source.ifc').resolve()),module['inputs'])
        altered=copy.deepcopy(module);altered['payload']['spaces'][0]['height_m']+=1
        (out/'recognition/result.json').write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError,'verified nested result'):verify_result(out/'recognition/result.json')

    def test_disabled_and_missing_runtime_gate_dependents_only(self):
        for name,kwargs in [('disabled',dict(disabled_module_providers=['moosas.ifc-room-recognition'])),('missing',dict(runtime={}))]:
            r,out=self.execute(name,**kwargs)
            self.assertEqual(r['tasks']['recognition']['status'],'pending');self.assertEqual(r['tasks']['lighting-rules']['status'],'pending')
            self.assertEqual(r['tasks']['independent-electrical']['status'],'pass')
            self.assertFalse((out/'recognition/intake').exists())

    def test_unrecognized_settings_fail_without_native_extraction(self):
        setting=self.plan.parent/'native-settings.json';data=json.loads(setting.read_text());data['command']='not executable';setting.write_text(json.dumps(data))
        request=self.plan.parent/'native-request.json';data=json.loads(request.read_text());data['sources']['settings']['sha256']=digest(setting);request.write_text(json.dumps(data))
        r,out=self.execute('bad-settings')
        self.assertEqual(r['tasks']['recognition']['status'],'fail');self.assertEqual(r['tasks']['lighting-rules']['status'],'pending')
        self.assertFalse((out/'recognition/intake').exists())

    def test_lighting_basis_cannot_drop_a_native_guid(self):
        basis=self.plan.parent/'lighting-basis.json';data=json.loads(basis.read_text());data.pop(next(iter(data)));basis.write_text(json.dumps(data))
        r,_=self.execute('dropped-guid')
        self.assertEqual(r['tasks']['recognition']['status'],'pass');self.assertEqual(r['tasks']['lighting-rules']['status'],'fail')
        self.assertEqual(r['tasks']['independent-electrical']['status'],'pass')
