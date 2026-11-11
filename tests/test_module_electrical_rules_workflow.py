import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
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
