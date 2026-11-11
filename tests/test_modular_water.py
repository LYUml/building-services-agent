import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.delivery import context
from bsa.modules import run,verify_result
from bsa.module_contract import validate
from bsa.workflow import execute,verify
from bsa.workflow_status import diagnose
from bsa.providers import epanet_water

ROOT=Path(__file__).resolve().parents[1]


class ModularWaterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('modular-water-plan.json','modular/water-graph.json','modular/water-graph-brief.md','water-loop/project.json'):
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'examples'/name,dest)
        self.plan=self.root/'modular-water-plan.json';self.request=self.root/'modular/water-graph.json';self.source=self.root/'water-loop/project.json'

    def change(self,transform):
        p=json.loads(self.source.read_text());transform(p);self.source.write_text(json.dumps(p))
        request=json.loads(self.request.read_text());request['sources']['project']['sha256']=digest(self.source);self.request.write_text(json.dumps(request))

    def scenario(self,name='good'):
        out=self.root/name;workflow=execute(self.plan,out);path=out/'water/result.json';return out,workflow,verify_result(path)

    def test_real_loop_signed_flow_native_files_and_pending_acceptance(self):
        out,w,m=self.scenario();self.assertTrue(verify(out)['integrity_pass']);self.assertTrue(context(self.plan,out))
        self.assertEqual(w['tasks']['water']['status'],'pass');self.assertEqual(m['execution']['status'],'completed')
        p=m['payload'];self.assertEqual(p['units'],dict(flow='m3/s',head='m',velocity='m/s'))
        self.assertEqual(p['pressure_basis'],'static pressure head in metres of water');self.assertFalse(p['geometry_bound'])
        pipes={r['id']:r for r in p['pipes']};self.assertAlmostEqual(pipes['CB']['flow_m3_s'],-.001,delta=1e-7)
        self.assertFalse(m['design_accepted']);self.assertEqual(m['acceptance']['status'],'pending')
        self.assertEqual(w['tasks']['review']['status'],'pending')
        for name in ('network.inp','network.rpt','raw.json','worker.log'):self.assertTrue((out/'water/analysis'/name).is_file())
        self.assertNotIn('electrical_power_kw',p['pumps'][0])

    def test_completed_shortfall_is_numerical_fail_and_false_workflow_pass_rejects(self):
        self.change(lambda p:p['pumps'][0].update(head_curve=[[0,20],[.002,15],[.004,10],[.008,2]]))
        out,w,m=self.scenario();self.assertEqual(m['execution']['status'],'completed');self.assertEqual(m['payload']['status'],'fail')
        self.assertFalse(m['payload']['checks']['delivery_targets']);self.assertEqual(w['tasks']['water']['status'],'fail')
        self.assertIn('required checks unresolved',w['tasks']['review']['scope'])
        self.assertEqual(diagnose(self.plan,out)['tasks'][0]['module_state']['numerical_result']['status'],'fail')
        w['tasks']['water']['status']='pass'
        for r in w['requirements']:
            if r['task']=='water':r['execution_status']='pass'
        (out/'workflow.json').write_text(json.dumps(w))
        with self.assertRaisesRegex(ValueError,'contradicts retained module'):context(self.plan,out)

    def test_common_head_forgery_and_raw_replay_forgery_reject(self):
        out,_,m=self.scenario();path=out/'water/result.json'
        m['payload']['junctions'][0]['static_pressure_head_m']+=1;path.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Common water graph'):verify_result(path)
        # A coherent domain-report/hash edit still cannot bypass source/raw replay.
        report_path=out/'water/analysis/water.json';report=json.loads(report_path.read_text())
        report['junctions'][0]['head_m']+=1;report_path.write_text(json.dumps(report))
        m['payload']['report']['sha256']=digest(report_path);m['artifacts']['analysis/water.json']=digest(report_path);path.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'numerical replay'):verify_result(path)

    def test_schema_rejects_pressure_unit_claim_duplicate_ids_and_path_escape(self):
        _,_,m=self.scenario();p=m['payload']
        for mutate in (lambda v:v['units'].update(head='Pa'),lambda v:v['junctions'].append(copy.deepcopy(v['junctions'][0])),lambda v:v['raw'].update(path='../raw.json')):
            bad=copy.deepcopy(p);mutate(bad)
            with self.assertRaises(ValueError):validate(bad)

    def test_disable_invalid_input_and_runtime_incompatible_are_distinct(self):
        out=self.root/'disabled';w=execute(self.plan,out,disabled_module_providers=['wntr.epanet-steady']);m=verify_result(out/'water/result.json')
        self.assertEqual(w['tasks']['water']['status'],'pending');self.assertIsNone(m['payload']);self.assertFalse((out/'water/analysis').exists())
        version=epanet_water.importlib.metadata.version
        with patch.object(epanet_water.importlib.metadata,'version',side_effect=lambda name:'0.0' if name=='wntr' else version(name)):
            m=run(self.request,'wntr.epanet-steady',self.root/'wrong-runtime')
        self.assertEqual(m['execution']['status'],'unavailable');self.assertEqual(m['execution']['diagnostics'][0]['code'],'runtime_incompatible')
        self.change(lambda p:p['pipes'][0].update(diameter_m=0));_,w,m=self.scenario('invalid')
        self.assertEqual(m['execution']['status'],'failed');self.assertIsNone(m['payload']);self.assertEqual(w['tasks']['water']['status'],'fail')

    def test_explicit_policy_worker_failure_has_no_hydraulic_payload(self):
        def blocked(command,**kwargs):
            folder=Path(command[-1]);folder.mkdir()
            (folder/'worker.log').write_text('An Application Control policy has blocked this file.')
            (folder/'water.json').write_text(json.dumps(dict(engine_failure=dict(kind='application_control_block'))))
            return __import__('subprocess').CompletedProcess(command,2,'','')
        with patch.object(epanet_water.subprocess,'run',side_effect=blocked):
            m=run(self.request,'wntr.epanet-steady',self.root/'policy-control')
        self.assertEqual(m['execution']['status'],'failed');self.assertIsNone(m['payload'])
        self.assertEqual(m['execution']['diagnostics'][0]['code'],'application_control_block')
