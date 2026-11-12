import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.modules import run,verify_result
from bsa.module_contract import validate

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit pinned MOOSAS runtime trial required')
class MoosasRecognitionProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.runtime=dict(upstream=ROOT/'tools/moosas-review',deps=ROOT/'tools/moosas-exchange-deps')

    def request(self,fixture):
        path=self.root/(fixture+'-request.json')
        sources={role:dict(path=os.path.relpath(p,path.parent),sha256=digest(p)) for role,p in [('geometry',ROOT/f'examples/moosas-transform/{fixture}.geo'),('expectations',ROOT/f'examples/moosas-transform/{fixture}.expected.json')]}
        path.write_text(json.dumps(dict(schema='bsa.module-request/1',project_id='synthetic-source-controls',scenario_id=fixture,capability='spatial.surface-room-recognition',coordinate_frame=dict(id='declared-planar-metres',kind='source-world-si',length_unit='m',georeferenced=False),sources=sources)))
        return path

    def test_actual_nonrectangular_rotated_and_notched_sources(self):
        for fixture in ('l-shaped-room','rotated-room','narrow-notch'):
            output=self.root/fixture
            result=run(self.request(fixture),'moosas.surface-room-recognition',output,runtime=self.runtime)
            self.assertEqual(result['execution']['status'],'completed',result['execution'])
            verify_result(output/'result.json')
            self.assertEqual(result['payload']['spaces'][0]['id'],fixture)
            self.assertEqual(result['payload']['spaces'][0]['floor_elevation_m'],0)
            self.assertEqual(result['acceptance']['status'],'pending')
            self.assertFalse(result['payload']['simulation_ready'])

    def test_disabled_missing_runtime_and_wrong_source_expectation(self):
        request=self.request('l-shaped-room')
        for label,kwargs in [('disabled',dict(disabled=True)),('missing',{})]:
            r=run(request,'moosas.surface-room-recognition',self.root/label,**kwargs)
            self.assertEqual(r['execution']['status'],'unavailable');verify_result(self.root/label/'result.json')
        changed=json.loads((ROOT/'examples/moosas-transform/l-shaped-room.expected.json').read_text())
        changed['expected'][0]['floor_elevation_m']=1
        expectation=self.root/'wrong-elevation.json';expectation.write_text(json.dumps(changed))
        data=json.loads(request.read_text());data['sources']['expectations']=dict(path=expectation.name,sha256=digest(expectation));request.write_text(json.dumps(data))
        r=run(request,'moosas.surface-room-recognition',self.root/'wrong',runtime=self.runtime)
        self.assertEqual(r['execution']['status'],'failed');self.assertIsNone(r['payload'])

    def test_common_payload_change_rejects_source_check(self):
        output=self.root/'mutated';r=run(self.request('rotated-room'),'moosas.surface-room-recognition',output,runtime=self.runtime)
        for kind in ('duplicate','area','frame'):
            changed=copy.deepcopy(r['payload'])
            if kind=='duplicate':changed['spaces'].append(copy.deepcopy(changed['spaces'][0]))
            elif kind=='area':changed['spaces'][0]['floor_area_m2']*=2
            else:changed['coordinate_frame']['length_unit']='mm'
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate(changed)
        altered=copy.deepcopy(r);altered['payload']['spaces'][0]['height_m']+=1
        validate(altered);(output/'result.json').write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError,'source check'):verify_result(output/'result.json')
