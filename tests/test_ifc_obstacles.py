import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_obstacles import prepare,run

ROOT=Path(__file__).resolve().parents[1]


class GeneralObstacleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        source=ROOT/'examples/cable-coordination'
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(source/'project.json',source/'geometry.json',cls.root/'cable','mixed-revolution')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_native_append_preserves_all_original_entities(self):
        source=ROOT/'examples/cable-coordination/obstacles.json';ifc=self.root/'cable/cables.ifc';before=digest(ifc)
        r=run(ifc,source,self.root/'appended')
        self.assertEqual(digest(ifc),before);self.assertTrue(r['original_entities_unchanged'])
        self.assertAlmostEqual(r['obstacles'][0]['saved_volume_m3'],.04*.04*.06)
        self.assertEqual(r['obstacles'][0]['properties']['SourceKind'],'assumption')
        self.assertFalse(r['design_accepted'])
        with self.assertRaisesRegex(ProjectError,'already exists'):run(self.root/'appended/model.ifc',source,self.root/'duplicate')

    def test_source_and_dimension_errors_rejected(self):
        folder=self.root/'invalid';shutil.copytree(ROOT/'examples/cable-coordination',folder)
        inventory=folder/'obstacles.json';original=inventory.read_bytes();p=json.loads(original)
        p['obstacles'][0]['size_m'][0]=0;inventory.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'positive sizes'):prepare(inventory)
        inventory.write_bytes(original)
        with (folder/'basis.json').open('a') as f:f.write('changed')
        with self.assertRaisesRegex(ProjectError,'source path/hash'):prepare(inventory)

    def test_external_output_requires_explicit_host_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'combined'
            source=ROOT/'examples/cable-coordination/obstacles.json'
            ifc=self.root/'cable/cables.ifc'
            with patch.dict('os.environ',{},clear=True):
                with self.assertRaisesRegex(ProjectError,'host-selected workspace'):
                    run(ifc,source,target)
            with patch.dict('os.environ',{'BSA_PROJECT_ROOT':folder}):
                r=run(ifc,source,target)
                self.assertTrue(r['original_entities_unchanged'])
                self.assertTrue(r['calculated_checks_pass'])
                self.assertFalse(r['design_accepted'])

    def test_multiple_native_contexts_require_explicit_selection(self):
        import ifcopenshell
        from bsa.obstacle_boxes import append
        model=ifcopenshell.open(str(self.root/'cable/cables.ifc'))
        context=next(c for c in model.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier=='Body')
        model.create_entity('IfcGeometricRepresentationSubContext',ContextIdentifier='Body',
            ContextType='Model',ParentContext=context.ParentContext,TargetView='MODEL_VIEW')
        path=self.root/'multiple-contexts.ifc';model.write(str(path))
        rows=[dict(id='explicit',origin_m=[5.,5.,5.],size_m=[1.,1.,1.],source='Synthetic context selection control')]
        kwargs=dict(prefix='CONTEXT_',pset_name='BSA_Test',metadata={})
        with self.assertRaisesRegex(ProjectError,'body context'):
            append(path,rows,set(),self.root/'ambiguous',**kwargs)
        with self.assertRaisesRegex(ProjectError,'body context'):
            append(path,rows,set(),self.root/'wrong-context',body_context_id=999999,**kwargs)
        r=append(path,rows,set(),self.root/'explicit-context',body_context_id=context.id(),**kwargs)
        self.assertEqual(r['body_context_id'],context.id())
        self.assertTrue(r['original_entities_unchanged'])
