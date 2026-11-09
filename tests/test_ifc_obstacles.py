import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
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
