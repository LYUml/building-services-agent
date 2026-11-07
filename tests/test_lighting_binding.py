import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.lighting_binding import prepare,run
from bsa.engine import ProjectError
from bsa.workflow import execute
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class BoundLightingTests(unittest.TestCase):
    def inputs(self):
        return tuple(json.loads((ROOT/'examples'/p).read_text()) for p in (
            'office-electrical/project.json','office-electrical/geometry.json','shared-lighting.json'))

    def test_shared_origins_and_translated_room_frame(self):
        e,g,o=self.inputs()
        p,files,bindings,origin=prepare(e,g,o,ROOT/'examples')
        self.assertEqual(p['luminaires'][0]['position_m'],[2,3,2.725])
        self.assertEqual(bindings[0]['ies_input_watts'],40)
        self.assertEqual(bindings[0]['electrical_kw'],0.04)
        self.assertEqual(len(files),1)
        g['spaces'][0]['origin_m']=[10,20,30]
        for d in e['devices']:d['x_m']+=10;d['y_m']+=20
        for d in g['devices']:d['z_m']+=30
        for s in o['sensors']:s['position_m']=[a+b for a,b in zip(s['position_m'],[10,20,30])]
        changed,_,_,origin=prepare(e,g,o,ROOT/'examples')
        self.assertEqual(origin,[10,20,30])
        for a,b in zip(changed['luminaires'][0]['position_m'],p['luminaires'][0]['position_m']):self.assertAlmostEqual(a,b,places=10)
        for a,b in zip(changed['sensors'][0]['position_m'],p['sensors'][0]['position_m']):self.assertAlmostEqual(a,b,places=10)

    def test_missing_mapping_duplicated_values_and_power_mismatch_rejected(self):
        e,g,o=self.inputs()
        for mutate in (lambda p:p['photometry'].pop(),lambda p:p['photometry'][0].update(position_m=[2,3,2.7]),
                       lambda p:p['photometry'][0].update(origin_offset_m=[0,0]),
                       lambda p:p['power_check'].update(absolute_tolerance_w=-1)):
            candidate=copy.deepcopy(o);mutate(candidate)
            with self.assertRaises(ProjectError):prepare(e,g,candidate,ROOT/'examples')
        e['devices'][0]['electrical_kw']=0.06
        with self.assertRaises(ProjectError):prepare(e,g,o,ROOT/'examples')

    def test_bound_workflow_keeps_all_original_sources_and_missing_engine_pending(self):
        e,g,o=self.inputs()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'lighting').mkdir()
            shutil.copyfile(ROOT/'examples/lighting/synthetic-1000cd.ies',root/'lighting/synthetic-1000cd.ies')
            for name,data in (('electrical.json',e),('geometry.json',g),('optical.json',o)):
                (root/name).write_text(json.dumps(data))
            brief=root/'brief.md';brief.write_text('Bind these shared fixture positions to photometry.\n')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='light',kind='electrical_lighting',project='electrical.json',geometry='geometry.json',optical='optical.json')],
                requirements=[dict(id='R1',passage='P001',quote='Bind these shared fixture positions to photometry.',task='light',acceptance='shared coordinate binding')])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            result=execute(path,root/'run')
            self.assertEqual(result['tasks']['light']['status'],'pending')
            for name in ('geometry.json','optical.json','lighting/synthetic-1000cd.ies'):
                self.assertIn(str(root/name),result['inputs'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_RADIANCE_BIN') and importlib.util.find_spec('ifcopenshell'),
                         'requires Radiance binaries and IFC library')
    def test_real_bound_generation_and_simulation(self):
        e,g,o=self.inputs()
        o['reflectances'].update(wall=0,floor=0,ceiling=0)
        o['simulation'].update(ambient_bounces=1,ambient_divisions=64,verification_bounces=2,verification_divisions=128)
        o['sensors']=o['sensors'][:2]
        root=ROOT/'runs';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            root=Path(folder);(root/'lighting').mkdir()
            shutil.copyfile(ROOT/'examples/lighting/synthetic-1000cd.ies',root/'lighting/synthetic-1000cd.ies')
            paths=[]
            for name,data in (('electrical.json',e),('geometry.json',g),('optical.json',o)):
                path=root/name;path.write_text(json.dumps(data));paths.append(path)
            result=run(*paths,root/'run',Path(os.environ['BSA_TEST_RADIANCE_BIN']))
            self.assertTrue(result['calculated_checks_pass'])
            self.assertTrue(result['inputs_unchanged'])
            self.assertEqual({x['id'] for x in result['bindings']},{'L1','L2','L3'})
            self.assertTrue((root/'run/shared/bim/model.ifc').is_file())
            self.assertTrue((root/'run/shared/electrical/devices.dxf').is_file())
            self.assertFalse(result['design_accepted'])


if __name__=='__main__':unittest.main()
