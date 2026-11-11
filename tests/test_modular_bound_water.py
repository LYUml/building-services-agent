import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.delivery import context
from bsa.module_contract import validate
from bsa.modules import run,verify_result
from bsa.workflow import execute,verify
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class ModularBoundWaterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('modular-bound-water-plan.json','modular/water-authoring.json','modular/bound-water-graph.json','modular/bound-water-brief.md','water-loop-ifc/project.json','water-loop-ifc/model.json','water-loop-ifc/binding.json'):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'examples'/name,path)
        self.plan=self.root/'modular-bound-water-plan.json';self.project=self.root/'water-loop-ifc/project.json';self.request=self.root/'modular/bound-water-graph.json'

    def change(self,transform):
        p=json.loads(self.project.read_text());transform(p);self.project.write_text(json.dumps(p))
        r=json.loads(self.request.read_text());r['sources']['project']['sha256']=digest(self.project);self.request.write_text(json.dumps(r))

    def test_actual_native_inheritance_derives_dimensions_and_preserves_model(self):
        out=self.root/'good';w=execute(self.plan,out);r=verify_result(out/'water/exchange/result.json');p=r['payload']
        self.assertEqual(w['tasks']['water']['status'],'pass');self.assertTrue(p['geometry_bound']);self.assertFalse(p['design_accepted'])
        generated=out/'water/exchange'/p['network_input']['path'];network=json.loads(generated.read_text())
        self.assertEqual({r['id']:r['length_m'] for r in network['pipes']},{'JA':5,'JB':7,'AC':7,'CB':5})
        self.assertTrue(all(abs(r['diameter_m']-.04)<1e-10 for r in network['pipes']))
        authored=verify_result(out/'model/result.json');self.assertEqual(authored['payload']['model']['sha256'],p['model']['sha256'])
        self.assertTrue(verify(out)['integrity_pass']);self.assertTrue(diagnose(self.plan,out)['integrity_pass']);context(self.plan,out)
        self.assertEqual(w['tasks']['review']['status'],'pending')

    def test_numerical_fail_and_disabled_upstream_preserve_gates(self):
        self.change(lambda p:[r.update(maximum_velocity_m_s=.01) for r in p['pipes']])
        out=self.root/'velocity';w=execute(self.plan,out);m=verify_result(out/'water/exchange/result.json')
        self.assertEqual(m['execution']['status'],'completed');self.assertEqual(m['payload']['status'],'fail')
        self.assertEqual(w['tasks']['water']['status'],'fail');self.assertIn('required checks unresolved',w['tasks']['review']['scope'])
        context(self.plan,out)
        w['tasks']['water']['status']='pass'
        for row in w['requirements']:
            if row['task']=='water':row['execution_status']='pass'
        (out/'workflow.json').write_text(json.dumps(w))
        with self.assertRaisesRegex(ValueError,'contradicts retained module'):context(self.plan,out)
        out=self.root/'disabled';w=execute(self.plan,out,disabled_module_providers=['ifcopenshell.bim-authoring'])
        self.assertEqual(w['tasks']['water']['status'],'pending');self.assertFalse((out/'water/exchange/result.json').exists())
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)

    def test_repeated_geometry_and_native_connection_loss_reject(self):
        self.change(lambda p:p['pipes'][0].update(length_m=5))
        out=self.root/'repeated';w=execute(self.plan,out);m=verify_result(out/'water/exchange/result.json')
        self.assertEqual(m['execution']['status'],'failed');self.assertIsNone(m['payload'])
        self.change(lambda p:p['pipes'][0].pop('length_m'))
        # Direct saved-IFC input exercises the real connection reader,not just authoring metadata.
        import ifcopenshell
        authored=verify_result(out/'model/result.json');source=out/'model'/authored['payload']['model']['path']
        model=ifcopenshell.open(str(source));model.remove(model.by_type('IfcRelConnectsPorts')[0]);changed=self.root/'disconnected.ifc';model.write(str(changed))
        request=json.loads(self.request.read_text());request['sources']['ifc']=dict(path='../disconnected.ifc',sha256=digest(changed));direct=self.root/'modular/direct.json';direct.write_text(json.dumps(request))
        m=run(direct,'wntr.ifc-steady',self.root/'native-failure')
        self.assertEqual(m['execution']['status'],'failed');self.assertIsNone(m['payload'])

    def test_common_head_forgery_and_wrong_units_reject(self):
        out=self.root/'forged';w=execute(self.plan,out);path=out/'water/exchange/result.json';m=verify_result(path)
        m['payload']['junctions'][0]['head_m']+=1;path.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Common bound water'):verify_result(path)
        m['payload']['units']['head']='Pa'
        with self.assertRaises(ValueError):validate(m)
