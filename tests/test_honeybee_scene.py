import json
from pathlib import Path
import runpy
import tempfile
import unittest
import ifcopenshell
from bsa.bim import run as author
from bsa.concept_facade import run as facade
from bsa.honeybee_scene import run
from bsa.cli import digest
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];PYTHON=ROOT/'tools/honeybee-scene-runtime/Scripts/python.exe'

@unittest.skipUnless(PYTHON.is_file(),'requires pinned isolated Honeybee scene runtime')
class HoneybeeSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        stage=runpy.run_path(str(ROOT/'scripts/run_public_massing.py'))['stage']
        decisions=json.loads((ROOT/'benchmarks/mit-4401-2018/massing-decisions.json').read_text(encoding='utf-8'))
        source=stage(decisions,dict(id='synthetic-grid-test',width_m=5,depth_m=4,storeys=2))
        data=dict(project=source,layout=dict(source='Synthetic comparison',window_wall_ratio=.4,layout='centered-equal-fraction'),basis=dict(source='Synthetic thickness choices, not product data',wall_thickness_m=.2,window_envelope_thickness_m=.04))
        for name,row in data.items():(cls.root/(name+'.json')).write_text(json.dumps(row),encoding='utf-8')
        doc=cls.root/'test-source.txt';doc.write_text('Explicit synthetic scene fixture, no course or product acceptance',encoding='utf-8')
        settings=dict(source='Synthetic optical/grid QA only',documents={'test-source.txt':digest(doc)},reflectance=dict(wall=.5,floor=.2,ceiling=.8),visible_transmittance=.7,grid_spacing_m=.5,sensor_height_m=.85)
        (cls.root/'scene-basis.json').write_text(json.dumps(settings),encoding='utf-8')
        author(cls.root/'project.json',cls.root/'model')
        facade(cls.root/'model/model.ifc',cls.root/'project.json',cls.root/'layout.json',cls.root/'basis.json',cls.root/'facade')
        cls.result=cls.convert(cls.root/'positive')

    @classmethod
    def convert(cls,out,ifc=None,scene=None):return run(ifc or cls.root/'facade/facade.ifc',cls.root/'project.json',cls.root/'layout.json',cls.root/'basis.json',scene or cls.root/'scene-basis.json',out,PYTHON)

    def test_saved_rooms_apertures_exact_sensor_grid_and_no_simulated_results(self):
        r=self.result
        self.assertEqual(r['rooms'],2);self.assertEqual(r['apertures'],8);self.assertEqual(r['sensor_count'],160)
        self.assertEqual(r['rad_polygon_count'],20);self.assertTrue(r['exported_punched_area_checks_pass'])
        self.assertAlmostEqual(r['aperture_area_m2'],2*(5+4)*3.5*2*.4)
        self.assertTrue(r['geometry_checks_pass']);self.assertFalse(r['simulation_executed']);self.assertFalse(r['solver_ready']);self.assertFalse(r['design_accepted'])
        self.assertEqual(r['optical_conversion']['source_visible_transmittance'],.7)
        self.assertAlmostEqual(r['optical_conversion']['saved_glass_transmissivity'],.7628419848230164)
        self.assertNotEqual(r['optical_conversion']['saved_glass_transmissivity'],.7)
        for name in r['artifacts']:self.assertEqual(digest(self.root/'positive'/name),r['artifacts'][name])

    def test_missing_or_changed_source_and_invalid_sensor_settings_reject(self):
        original=json.loads((self.root/'scene-basis.json').read_text(encoding='utf-8'))
        for mode in ('source','sensor','optical'):
            row=json.loads(json.dumps(original))
            if mode=='source':row['documents']['test-source.txt']='wrong'
            if mode=='sensor':row['sensor_height_m']=True
            if mode=='optical':row['visible_transmittance']=1
            path=self.root/(mode+'.json');path.write_text(json.dumps(row),encoding='utf-8');out=self.root/('reject-'+mode)
            with self.subTest(mode=mode),self.assertRaises(ProjectError):self.convert(out,scene=path)
            self.assertFalse(out.exists())

    def test_native_window_mutation_rejects_before_scene_creation(self):
        m=ifcopenshell.open(str(self.root/'facade/facade.ifc'));m.by_type('IfcWindow')[0].OverallWidth+=1
        path=self.root/'changed.ifc';m.write(str(path));out=self.root/'reject-native'
        with self.assertRaises(ProjectError):self.convert(out,ifc=path)
        self.assertFalse(out.exists())
