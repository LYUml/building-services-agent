import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.workflow import validate_plan,verify
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'runs/public-brief-intake-v1/sources'

@unittest.skipUnless((CACHE/'assignment5.pdf').is_file(),'requires pinned public source cache')
class ConceptLayoutWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)/'case'
        cls.result=runpy.run_path(str(ROOT/'scripts/run_public_massing.py'))['run_workflow'](cls.root,CACHE)

    def test_native_layout_artifacts_and_sources_are_inventoried(self):
        report=json.loads((self.root/'workflow/workflow.json').read_text(encoding='utf-8'))
        self.assertEqual(self.result['pending_interpretation_tasks'],34)
        for label,count in [('compact',8),('slender',8),('stacked',16)]:
            artifact='concept-'+label+'/concept-layout/geometry-handoff.json'
            self.assertIn(artifact,report['artifact_hashes'])
            r=json.loads((self.root/'workflow'/artifact).read_text(encoding='utf-8'))
            self.assertEqual(len(r['draft_window_rectangles']),count)
            self.assertFalse(r['thermal_model_ready'])
            self.assertIn(str(self.root/(label+'-layout.json')),report['inputs'])
        self.assertTrue(verify(self.root/'workflow')['integrity_pass'])
        artifact=self.root/'workflow/concept-compact/concept-layout/geometry-handoff.json'
        original=artifact.read_bytes()
        try:
            artifact.write_bytes(original+b' ')
            self.assertFalse(verify(self.root/'workflow')['integrity_pass'])
        finally:artifact.write_bytes(original)

    def test_invalid_settings_and_nonconcept_scope_reject_before_execution(self):
        settings=self.root/'compact-layout.json';original=settings.read_bytes()
        try:
            row=json.loads(original)
            for key,value in [('window_wall_ratio',True),('source',''),('layout','invented')]:
                bad=copy.deepcopy(row);bad[key]=value
                settings.write_text(json.dumps(bad),encoding='utf-8')
                with self.assertRaises(ProjectError):validate_plan(self.root/'plan.json')
        finally:settings.write_bytes(original)
        project=self.root/'compact.json';original=project.read_bytes()
        try:
            row=json.loads(original);row['geometry_scope']='axis-aligned bounding envelopes'
            project.write_text(json.dumps(row),encoding='utf-8')
            with self.assertRaisesRegex(ProjectError,'concept BIM scope'):validate_plan(self.root/'plan.json')
        finally:project.write_bytes(original)
