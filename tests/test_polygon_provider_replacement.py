import copy
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.modules import verify_result
from bsa.module_contract import validate

ROOT=Path(__file__).resolve().parents[1]


class PolygonProviderReplacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        source=runpy.run_path(str(ROOT/'examples/moosas-transform/build_ifc.py'))['build'](cls.root/'source')
        cls.plan=runpy.run_path(str(ROOT/'examples/moosas-transform/build_workflow.py'))['build'](cls.root/'inputs',ifc_source=source,tolerances=dict(length_tolerance_m=1e-6,area_tolerance_m2=1e-8))
        # Rule dispatch/source-hash control only;retained trials use actual official bytes.
        official=cls.plan.parent/'sources/emsd-bec-2024.pdf';official.write_bytes(b'SYNTHETIC TEST SOURCE ONLY')
        pack=cls.plan.parent/'lighting-pack.json';data=json.loads(pack.read_text());data['sources']['emsd_bec_2024']['sha256']=digest(official);pack.write_text(json.dumps(data))

    def execute(self,name,**kwargs):
        out=self.root/name;r=execute(self.plan,out,**kwargs)
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
        return r,out

    def test_native_no_moosas_runtime_and_source_replay(self):
        r,out=self.execute('native',module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        self.assertEqual(r['tasks']['recognition']['status'],'pass');self.assertEqual(r['tasks']['lighting-rules']['status'],'pass')
        module=verify_result(out/'recognition/result.json');self.assertIsNone(module['payload']['point_grid_m'])
        self.assertEqual(sorted(s['floor_area_m2'] for s in module['payload']['spaces']),[14,24,30])
        self.assertFalse((out/'recognition/recognition').exists())
        changed=copy.deepcopy(module['payload']);changed['point_grid_m']=.001
        with self.assertRaises(ValueError):validate(changed)
        changed=copy.deepcopy(module);changed['payload']['spaces'][0]['height_m']+=1
        (out/'recognition/result.json').write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'saved-source replay'):verify_result(out/'recognition/result.json')

    def test_native_disable_and_incompatible_provider(self):
        r,_=self.execute('disabled-native',module_providers={'recognition':'ifcopenshell.polygon-spaces'},disabled_module_providers=['ifcopenshell.polygon-spaces'])
        self.assertEqual(r['tasks']['recognition']['status'],'pending');self.assertEqual(r['tasks']['lighting-rules']['status'],'pending')
        self.assertEqual(r['tasks']['independent-electrical']['status'],'pass')
        with self.assertRaises(ValueError):execute(self.plan,self.root/'incompatible',module_providers={'recognition':'ifcopenshell.box-spaces'})
        self.assertFalse((self.root/'incompatible').exists())

    def test_native_external_project_without_moosas_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder).resolve()
            shutil.copytree(self.plan.parent,project/'inputs')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(project)}):
                out=project/'workflow';plan=project/'inputs/plan.json'
                result=execute(plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'})
                self.assertEqual(result['tasks']['recognition']['status'],'pass')
                self.assertEqual(result['tasks']['lighting-rules']['status'],'pass')
                self.assertTrue(verify(out)['integrity_pass']);context(plan,out)
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaises(ValueError):verify_result(out/'recognition/result.json')

    @unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit MOOSAS runtime required')
    def test_actual_backend_switch_keeps_geometry_and_lighting_input(self):
        from shapely.geometry import Polygon
        _,native=self.execute('comparison-native',module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        _,moosas=self.execute('comparison-moosas',module_runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps'))
        a=verify_result(native/'recognition/result.json')['payload'];b=verify_result(moosas/'recognition/result.json')['payload']
        self.assertEqual(a['coordinate_frame'],b['coordinate_frame']);self.assertEqual(a['units'],b['units'])
        spaces={s['id']:s for s in b['spaces']};self.assertEqual({s['id'] for s in a['spaces']},set(spaces))
        for row in a['spaces']:
            other=spaces[row['id']]
            for field in ('floor_area_m2','height_m','floor_elevation_m'):self.assertAlmostEqual(row[field],other[field],places=8)
            first,second=Polygon(row['boundary_vertices']),Polygon(other['boundary_vertices'])
            self.assertLessEqual(first.hausdorff_distance(second),1e-6);self.assertLessEqual(first.symmetric_difference(second).area,1e-8)
        self.assertEqual((native/'lighting-rules/bound-space-projects.json').read_bytes(),(moosas/'lighting-rules/bound-space-projects.json').read_bytes())
