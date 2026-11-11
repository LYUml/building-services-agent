import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.workflow import execute,verify
from bsa.workflow_status import diagnose
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class ModularDrawingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('modular-drawing-plan.json','modular/drawing-authoring.json','modular/drawing-brief.md','water-loop-ifc/model.json','water-loop-ifc/views-settings.json'):
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/'examples'/name).read_bytes())
        self.plan=self.root/'modular-drawing-plan.json'

    def test_verified_model_artifact_feeds_complete_views_without_native_runtime(self):
        out=self.root/'run';result=execute(self.plan,out)
        self.assertEqual([r['status'] for r in result['tasks'].values()],['pass','pass','pending','pending'])
        self.assertTrue(verify(out)['integrity_pass']);self.assertTrue(diagnose(self.plan,out)['integrity_pass'])
        views=json.loads((out/'views/views.json').read_text())
        self.assertEqual(views['inputs'][str(out/'model/native/model.ifc')],digest(out/'model/native/model.ifc'))
        self.assertEqual(len(views['axis_coverage']),6);self.assertEqual(len(views['views']),3)
        self.assertFalse((out/'native').exists())

    def test_disabled_authoring_blocks_views_and_native_worker(self):
        runtime=self.root/'runtime.exe';runtime.write_text('Mock host runtime identity;never execute')
        with patch('bsa.ifc_views.run_native') as native:
            result=execute(self.plan,self.root/'disabled',autocad=runtime,disabled_module_providers=['ifcopenshell.bim-authoring'])
        native.assert_not_called();self.assertTrue(all(r['status']=='pending' for r in result['tasks'].values()))
        self.assertFalse((self.root/'disabled/views').exists())

    def test_missing_source_segment_label_blocks_native_generation(self):
        settings=self.root/'water-loop-ifc/views-settings.json';data=json.loads(settings.read_text())
        # Keep all references valid while omitting one other segment.
        refs={v['sheet']['reference_ifc_guid'] for v in data['views']}
        omitted=next(g for g in data['labels'] if g not in refs);data['labels'].pop(omitted);settings.write_text(json.dumps(data))
        runtime=self.root/'runtime.exe';runtime.write_text('Mock host runtime identity;never execute')
        with patch('bsa.ifc_views.run_native') as native:result=execute(self.plan,self.root/'incomplete',autocad=runtime)
        native.assert_not_called();self.assertEqual([r['status'] for r in result['tasks'].values()],['pass','fail','pending','pending'])
        self.assertFalse((self.root/'incomplete/native').exists())
