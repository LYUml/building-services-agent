import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.workflow import execute,verify,validate_plan
from bsa.delivery import context
from bsa.module_electrical_rules import run as assess,verify as verify_rules

ROOT=Path(__file__).resolve().parents[1]


class ElectricalRuleWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        cache=self.root/'empty';cache.mkdir()
        build=runpy.run_path(str(ROOT/'examples/modular/build_electrical_rules_inputs.py'))['build']
        self.plan=build(self.root/'inputs',cache);self.inputs=self.plan.parent
        # Synthetic hash/evaluator control;official-source execution is separate.
        source=self.inputs/'sources/emsd-wiring-2025.pdf';source.write_bytes(b'SYNTHETIC WORKFLOW SOURCE')
        pack=self.inputs/'source/pack.json';data=json.loads(pack.read_text());data['sources']['emsd_wiring_2025']['sha256']=digest(source);pack.write_text(json.dumps(data))

    def test_actual_chain_and_missing_source_keep_manual_review_pending(self):
        out=self.root/'positive';r=execute(self.plan,out)
        self.assertEqual([r['tasks'][k]['status'] for k in ('electrical','rules','review')],['pass','pass','pending'])
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        (self.inputs/'sources/emsd-wiring-2025.pdf').unlink();out=self.root/'missing';r=execute(self.plan,out)
        self.assertEqual(r['tasks']['rules']['status'],'pending');self.assertIn('required checks unresolved',r['tasks']['review']['scope']);context(self.plan,out)

    def test_registered_dispatch_equality_disable_and_declared_provider_identity(self):
        direct_out=self.root/'direct';execute(self.plan,direct_out)
        plan=json.loads(self.plan.read_text());plan['tasks'][1]['provider']='bsa.electrical-path-rules';self.plan.write_text(json.dumps(plan))
        out=self.root/'registered';r=execute(self.plan,out)
        baseline=assess(out/'electrical/result.json',self.inputs/'source/topology.json',self.inputs/'source/basis.json',self.inputs/'source/pack.json',self.inputs/'sources',self.root/'same-producer-direct')['assessment']
        self.assertEqual(r['tasks']['rules']['status'],'pass');self.assertEqual(verify_rules(out/'rules')['assessment'],baseline)
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        disabled=self.root/'rule-disabled';r=execute(self.plan,disabled,disabled_module_providers=['bsa.electrical-path-rules'])
        self.assertEqual(r['tasks']['rules']['status'],'pending');self.assertEqual(r['tasks']['review']['status'],'pending')
        self.assertTrue(verify(disabled)['integrity_pass']);context(self.plan,disabled)
        from bsa.workflow_status import diagnose
        rows={r['id']:r for r in diagnose(self.plan,disabled)['tasks']}
        self.assertEqual(rows['rules']['module_state']['execution']['diagnostics'][0]['code'],'provider_disabled')
        self.assertIn('enable the selected provider',rows['rules']['next_action'])
        plan['tasks'][1].pop('provider');self.plan.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):context(self.plan,out)

    def test_exceedance_false_pass_and_disabled_upstream(self):
        topology=self.inputs/'source/topology.json';data=json.loads(topology.read_text());data['feeders'][0]['route_length_m']=300;topology.write_text(json.dumps(data))
        out=self.root/'fail';r=execute(self.plan,out);self.assertEqual(r['tasks']['rules']['status'],'fail');context(self.plan,out)
        r['tasks']['rules']['status']='pass'
        for row in r['requirements']:
            if row['task']=='rules':row['execution_status']='pass'
        (out/'workflow.json').write_text(json.dumps(r))
        self.assertFalse(verify(out)['integrity_pass'])
        with self.assertRaisesRegex(ValueError,'contradicts retained result'):context(self.plan,out)
        out=self.root/'disabled';r=execute(self.plan,out,disabled_module_providers=['bsa.single-phase-circuits'])
        self.assertEqual(r['tasks']['rules']['status'],'pending');self.assertFalse((out/'rules/electrical-module-rules.json').exists());context(self.plan,out)

    def test_replacement_inputs_and_unsupported_release_consumer_reject(self):
        p=json.loads(self.plan.read_text());original=json.loads(self.plan.read_text());p['tasks'][1]['project']='source/project.json';self.plan.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError,'replacement inputs forbidden'):validate_plan(self.plan)
        original['tasks'][-1].update(kind='electrical',project='source/project.json');self.plan.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError,'same-producer handoff'):validate_plan(self.plan)

    def test_coherent_other_producer_report_cannot_replace_declared_lineage(self):
        out=self.root/'original';r=execute(self.plan,out);clone=self.root/'clone';shutil.copytree(out/'electrical',clone)
        fresh=self.root/'fresh';assess(clone/'result.json',self.inputs/'source/topology.json',self.inputs/'source/basis.json',self.inputs/'source/pack.json',self.inputs/'sources',fresh)
        for file in fresh.iterdir():shutil.copyfile(file,out/'rules'/file.name)
        verify_rules(out/'rules')
        for name in r['artifact_hashes']:
            if name.startswith('rules/'):r['artifact_hashes'][name]=digest(out/name)
        (out/'workflow.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'differ from declared producer'):context(self.plan,out)

    def test_native_missing_host_and_failed_rule_do_not_call_cad(self):
        build=runpy.run_path(str(ROOT/'examples/modular/build_electrical_rules_inputs.py'))['build']
        plan=build(self.root/'drawing-inputs',self.root/'empty',True);inputs=plan.parent
        shutil.copyfile(self.inputs/'sources/emsd-wiring-2025.pdf',inputs/'sources/emsd-wiring-2025.pdf')
        shutil.copyfile(self.inputs/'source/pack.json',inputs/'source/pack.json')
        with patch('bsa.module_electrical_native.run') as cad:
            out=self.root/'missing-cad';r=execute(plan,out)
        cad.assert_not_called();self.assertEqual(r['tasks']['rules']['status'],'pass');self.assertEqual(r['tasks']['native']['status'],'pending');context(plan,out)
        topology=inputs/'source/topology.json';data=json.loads(topology.read_text());data['feeders'][0]['route_length_m']=300;topology.write_text(json.dumps(data))
        exe=self.root/'never-launched.exe';exe.write_bytes(b'Not a program;CAD worker must not be called')
        with patch('bsa.module_electrical_native.run') as cad:
            out=self.root/'failed-rule-native';r=execute(plan,out,autocad=exe)
        cad.assert_not_called();self.assertEqual(r['tasks']['rules']['status'],'fail');self.assertEqual(r['tasks']['native']['status'],'pending')
        self.assertFalse((out/'native').exists());context(plan,out)

    def test_coincident_source_rejects_before_native_and_layout_preserves_electrical_data(self):
        from bsa.module_electrical_native import run
        out=self.root/'coincident';execute(self.plan,out)
        with patch('bsa.native_cad.convert') as convert:
            with self.assertRaisesRegex(ValueError,'Coincident device symbols'):
                run(out/'rules',self.root/'must-not-exist',self.root/'unused.exe')
        convert.assert_not_called();self.assertFalse((self.root/'must-not-exist').exists())
        build=runpy.run_path(str(ROOT/'examples/modular/build_electrical_rules_inputs.py'))['build']
        plan=build(self.root/'separated',self.root/'empty',True)
        original=json.loads((self.inputs/'source/project.json').read_text())
        staged=json.loads((plan.parent/'source/project.json').read_text())
        self.assertEqual(staged['circuits'],original['circuits'])
        for before,after in zip(original['devices'],staged['devices']):
            self.assertEqual({k:v for k,v in before.items() if k not in ('x_m','y_m')},
                             {k:v for k,v in after.items() if k not in ('x_m','y_m')})
        self.assertEqual(len({(d['x_m'],d['y_m']) for d in staged['devices']}),len(staged['devices']))
        from bsa.engine import calculate
        self.assertEqual(calculate(original),calculate(staged))
