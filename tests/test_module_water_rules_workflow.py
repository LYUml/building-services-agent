import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.delivery import context
from bsa.module_water_rules import run as assess,verify as verify_rules
from bsa.workflow import execute,verify,validate_plan,passages
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class ModuleWaterWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        cache=self.root/'empty-cache';cache.mkdir()
        build=runpy.run_path(str(ROOT/'examples/modular/build_water_rules_inputs.py'))['build']
        self.plan=build(self.root/'inputs',cache);self.inputs=self.plan.parent
        # Software control only;retained actual scenarios use the pinned official PDF.
        source=self.inputs/'sources/emsd-bec-2024.pdf';source.write_bytes(b'SYNTHETIC WORKFLOW TEST SOURCE')
        self.pack=self.inputs/'source/pack.json';p=json.loads(self.pack.read_text());p['sources']['emsd_bec_2024']['sha256']=digest(source);self.pack.write_text(json.dumps(p))
        self.basis=self.inputs/'source/regulatory-bases.json'

    def add(self,task,text):
        brief=self.inputs/'brief.md';brief.write_text(brief.read_text()+'\n'+text+'\n')
        rows=passages(brief);p=json.loads(self.plan.read_text());p['brief_sha256']=digest(brief);p['passage_dispositions'][rows[-1]['id']]='requirement';p['tasks'].append(task)
        p['requirements'].append(dict(id=task['id']+'-req',task=task['id'],passage=rows[-1]['id'],quote=text,acceptance=text));self.plan.write_text(json.dumps(p))

    def test_automatic_chain_and_missing_sources_preserve_pending_review(self):
        out=self.root/'positive';w=execute(self.plan,out)
        self.assertEqual([w['tasks'][k]['status'] for k in ('model','water','rules','review')],['pass','pass','pass','pending'])
        self.assertTrue(verify(out)['integrity_pass']);self.assertTrue(diagnose(self.plan,out)['integrity_pass']);context(self.plan,out)
        (self.inputs/'sources/emsd-bec-2024.pdf').unlink();out=self.root/'missing';w=execute(self.plan,out)
        self.assertEqual(w['tasks']['rules']['status'],'pending');self.assertIn('required checks unresolved',w['tasks']['review']['scope']);context(self.plan,out)

    def test_failed_rule_blocks_review_and_false_pass_rejects(self):
        p=json.loads(self.basis.read_text())
        for row in p['pipes'].values():row['water_pipe'].update(flow_mode=dict(value='variable',source='negative synthetic control'),pump_control=dict(value='single_fixed_speed',source='negative synthetic control'))
        self.basis.write_text(json.dumps(p));out=self.root/'failed';w=execute(self.plan,out)
        self.assertEqual(w['tasks']['rules']['status'],'fail');self.assertIn('required checks unresolved',w['tasks']['review']['scope']);context(self.plan,out)
        w['tasks']['rules']['status']='pass'
        for row in w['requirements']:
            if row['task']=='rules':row['execution_status']='pass'
        (out/'workflow.json').write_text(json.dumps(w))
        with self.assertRaisesRegex(ValueError,'contradicts retained result'):context(self.plan,out)
        self.assertFalse(verify(out)['integrity_pass'])

    def test_unavailable_upstream_produces_no_rule_report(self):
        out=self.root/'disabled';w=execute(self.plan,out,disabled_module_providers=['wntr.ifc-steady'])
        self.assertEqual(w['tasks']['rules']['status'],'pending');self.assertFalse((out/'rules/module-water-rules.json').exists())
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)

    def test_replacement_and_wrong_model_drawing_gates_reject(self):
        p=json.loads(self.plan.read_text());original=json.loads(self.plan.read_text());p['tasks'][2]['project']='source/project.json';self.plan.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError,'replacement inputs forbidden'):validate_plan(self.plan)
        self.plan.write_text(json.dumps(original))
        self.add(dict(id='other',kind='module_authoring',request='authoring-request.json',provider='ifcopenshell.bim-authoring'),'Author a separate comparison model.')
        shutil.copyfile(ROOT/'examples/water-loop-ifc/views-settings.json',self.inputs/'source/views.json')
        self.add(dict(id='views',kind='ifc_views',depends_on='other',settings='source/views.json',requires_pass=['rules']),'Draw that separate model using the earlier rule gate.')
        with self.assertRaisesRegex(ValueError,'same native authoring producer'):validate_plan(self.plan)
        p=json.loads(self.plan.read_text());p['tasks'][-1]['depends_on']='model';self.plan.write_text(json.dumps(p));validate_plan(self.plan)

    def test_valid_rule_report_from_another_producer_cannot_be_substituted(self):
        out=self.root/'original';w=execute(self.plan,out);clone=self.root/'clone';shutil.copytree(out/'water/exchange',clone)
        fresh=self.root/'fresh-rules';assess(clone/'result.json',self.basis,self.pack,self.inputs/'sources',fresh)
        for file in fresh.iterdir():shutil.copyfile(file,out/'rules'/file.name)
        verify_rules(out/'rules')
        for name in w['artifact_hashes']:
            if name.startswith('rules/'):w['artifact_hashes'][name]=digest(out/name)
        (out/'workflow.json').write_text(json.dumps(w))
        with self.assertRaisesRegex(ValueError,'inputs differ from declared producer'):context(self.plan,out)
