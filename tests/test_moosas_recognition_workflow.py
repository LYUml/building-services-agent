import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.delivery import context

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit pinned MOOSAS runtime trial required')
class MoosasRecognitionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.plan=runpy.run_path(str(ROOT/'examples/moosas-transform/build_workflow.py'))['build'](self.root/'inputs')
        self.runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps')
        # Test rule source hashing/dispatch only;these bytes are not official code.
        source=self.plan.parent/'sources/emsd-bec-2024.pdf';source.write_bytes(b'SYNTHETIC RULE SOURCE CONTROL ONLY')
        pack=self.plan.parent/'lighting-pack.json';data=json.loads(pack.read_text());data['sources']['emsd_bec_2024']['sha256']=digest(source);pack.write_text(json.dumps(data))

    def execute(self,name,**kwargs):
        out=self.root/name;r=execute(self.plan,out,module_runtime=self.runtime,**kwargs)
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        return r,out

    def test_enabled_geometry_rule_and_independent_tasks(self):
        r,out=self.execute('enabled')
        self.assertEqual({k:v['status'] for k,v in r['tasks'].items()},{'recognition':'pass','lighting-rules':'pass','review':'pending','independent-electrical':'pass'})
        bound=json.loads((out/'lighting-rules/bound-space-projects.json').read_text())
        self.assertEqual(bound['l-shaped-room']['lighting_space']['internal_floor_area']['value'],14)
        self.assertEqual(len(r['requirements']),4)

    def test_disabled_and_unknown_facts_gate_dependent_work(self):
        r,_=self.execute('disabled',disabled_module_providers=['moosas.surface-room-recognition'])
        self.assertEqual(r['tasks']['recognition']['status'],'pending');self.assertEqual(r['tasks']['lighting-rules']['status'],'pending');self.assertEqual(r['tasks']['independent-electrical']['status'],'pass')
        basis=self.plan.parent/'lighting-basis.json';data=json.loads(basis.read_text());data['l-shaped-room']['facts']['complete_fixed_lighting_inventory']['value']=None;basis.write_text(json.dumps(data))
        r,_=self.execute('unknown')
        self.assertEqual(r['tasks']['recognition']['status'],'pass');self.assertEqual(r['tasks']['lighting-rules']['status'],'pending')

    def test_exceeded_power_fails_selected_rule_without_changing_geometry(self):
        basis=self.plan.parent/'lighting-basis.json';data=json.loads(basis.read_text())
        for light in data['l-shaped-room']['lighting_space']['luminaires']:light['full_output_circuit_power']['value']=50
        basis.write_text(json.dumps(data));r,_=self.execute('exceeded')
        self.assertEqual(r['tasks']['recognition']['status'],'pass');self.assertEqual(r['tasks']['lighting-rules']['status'],'fail');self.assertEqual(r['tasks']['review']['status'],'pending')

    def test_missing_source_remains_pending(self):
        (self.plan.parent/'sources/emsd-bec-2024.pdf').unlink()
        r,_=self.execute('missing-source')
        self.assertEqual(r['tasks']['recognition']['status'],'pass');self.assertEqual(r['tasks']['lighting-rules']['status'],'pending')
