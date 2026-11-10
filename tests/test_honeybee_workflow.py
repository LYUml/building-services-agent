import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.workflow import validate_plan,execute,verify
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'runs/public-brief-intake-v1/sources';PYTHON=ROOT/'tools/honeybee-scene-runtime/Scripts/python.exe'

@unittest.skipUnless(PYTHON.is_file() and (CACHE/'assignment5.pdf').is_file(),'requires pinned Honeybee runtime and public source cache')
class HoneybeeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)/'case'
        cls.result=runpy.run_path(str(ROOT/'scripts/run_public_massing.py'))['run_workflow'](cls.root,CACHE,True,PYTHON)

    def test_actual_scene_inheritance_artifacts_and_unmet_packages(self):
        report=json.loads((self.root/'workflow/workflow.json').read_text(encoding='utf-8'))
        self.assertEqual(self.result['pending_work_packages'],14)
        self.assertIn(str(PYTHON),report['runtime_inputs'])
        for label in ('compact','slender','stacked'):
            r=json.loads((self.root/'workflow'/('scene-'+label)/'honeybee-scene.json').read_text(encoding='utf-8'))
            model=self.root/'workflow'/('facade-'+label)/'facade.ifc'
            from bsa.cli import digest
            self.assertEqual(r['inputs'][str(model)],digest(model))
            self.assertEqual(r['sensor_count'],14000);self.assertFalse(r['simulation_executed']);self.assertFalse(r['solver_ready'])
            self.assertIn('scene-'+label+'/scene/model.hbjson',report['artifact_hashes'])
            self.assertEqual(report['tasks']['scene-'+label]['status'],'pass')
        self.assertTrue(verify(self.root/'workflow')['integrity_pass'])
        path=self.root/'workflow/scene-compact/scene/grids/Space_Level1.pts';original=path.read_bytes()
        try:
            path.write_bytes(original+b' ')
            self.assertFalse(verify(self.root/'workflow')['integrity_pass'])
        finally:path.write_bytes(original)
        path=self.root/'workflow/workflow.json';original=path.read_bytes()
        try:
            changed=json.loads(original);changed['runtime_inputs'][str(PYTHON)]='wrong'
            path.write_text(json.dumps(changed),encoding='utf-8')
            self.assertFalse(verify(self.root/'workflow')['integrity_pass'])
        finally:path.write_bytes(original)

    def test_missing_runtime_leaves_pending_and_no_scene_folder(self):
        out=self.root/'missing-runtime';r=execute(self.root/'plan.json',out)
        for label in ('compact','slender','stacked'):
            self.assertEqual(r['tasks']['scene-'+label]['status'],'pending')
            self.assertIn('runtime not supplied',r['tasks']['scene-'+label]['scope'])
            self.assertFalse((out/('scene-'+label)).exists())

    def test_replacement_inputs_or_document_source_change_reject_before_run(self):
        plan=self.root/'plan.json';original=plan.read_bytes()
        try:
            row=json.loads(original);next(t for t in row['tasks'] if t['kind']=='honeybee_scene')['python']='from-document.exe'
            plan.write_text(json.dumps(row),encoding='utf-8')
            with self.assertRaisesRegex(ProjectError,'replacement/runtime'):validate_plan(plan)
        finally:plan.write_bytes(original)
        basis=self.root/'scene-basis.json';original=basis.read_bytes()
        try:
            row=json.loads(original);row['documents']['sources/assignment5.pdf']='wrong'
            basis.write_text(json.dumps(row),encoding='utf-8')
            with self.assertRaisesRegex(ProjectError,'source document identity'):validate_plan(plan)
        finally:basis.write_bytes(original)
