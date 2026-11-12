import copy
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.modules import run, verify_result
from bsa.module_contract import validate

ROOT=Path(__file__).resolve().parents[1]


class AirAllocationProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        plan=runpy.run_path(str(ROOT/'examples/hvac-package/build_inputs.py'))['build'](self.root/'inputs')
        data=json.loads(plan.read_text())
        task=next(t for t in data['tasks'] if t['kind']=='air_allocation')
        self.project=(plan.parent/task['project']).resolve()
        self.request=self.root/'request.json'
        self.request.write_text(json.dumps(dict(schema='bsa.module-request/1',project_id='public-control',scenario_id='allocation',capability='analysis.air.classified-allocation',coordinate_frame=dict(id='planar-metres',kind='source-world-si',length_unit='m',georeferenced=False),sources=dict(project=dict(path=os.path.relpath(self.project,self.root),sha256=digest(self.project))))))

    def test_actual_provider_replays_source_and_preserves_pending_acceptance(self):
        result=run(self.request,'bsa.classified-air-allocation',self.root/'output')
        self.assertEqual(result['execution']['status'],'completed')
        verify_result(self.root/'output/result.json')
        self.assertEqual(result['acceptance']['status'],'pending')
        self.assertEqual(result['payload']['units']['power'],'kW thermal')
        self.assertFalse(result['payload']['room_sensible_load_verified'])
        altered=copy.deepcopy(result)
        altered['payload']['terminals'][0]['minimum_flow_L_s']*=2
        with self.assertRaisesRegex(ValueError,'turndown'):validate(altered)
        altered=copy.deepcopy(result)
        altered['payload']['total_cooling_kW_thermal']*=2
        (self.root/'output/result.json').write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError,'source replay'):verify_result(self.root/'output/result.json')

    def test_disabled_and_source_change(self):
        result=run(self.request,'bsa.classified-air-allocation',self.root/'disabled',disabled=True)
        self.assertIsNone(result['payload']);verify_result(self.root/'disabled/result.json')
        run(self.request,'bsa.classified-air-allocation',self.root/'output')
        self.project.write_bytes(self.project.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'evidence changed'):verify_result(self.root/'output/result.json')

    def test_saved_report_rewrite_even_with_updated_hashes_rejects(self):
        result=run(self.request,'bsa.classified-air-allocation',self.root/'output')
        report=self.root/'output/analysis/allocation.json'
        data=json.loads(report.read_text());data['geometry_basis']='Invented source interpretation'
        report.write_text(json.dumps(data))
        result['artifacts']['analysis/allocation.json']=digest(report)
        result['payload']['report']['sha256']=digest(report)
        (self.root/'output/result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError,'source replay'):verify_result(self.root/'output/result.json')

    def test_contract_rejects_duplicate_ids_frame_and_unsafe_report_path(self):
        result=run(self.request,'bsa.classified-air-allocation',self.root/'output')
        for kind in ('id','frame','path'):
            payload=copy.deepcopy(result['payload'])
            if kind=='id':payload['terminals'][1]['id']=payload['terminals'][0]['id']
            elif kind=='frame':payload['coordinate_frame']['length_unit']='mm'
            else:payload['report']['path']='../escaped.json'
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate(payload)

    def test_unsupported_runtime_is_unavailable(self):
        import importlib.metadata
        original=importlib.metadata.version
        with patch('importlib.metadata.version',side_effect=lambda name:'0' if name=='shapely' else original(name)):
            result=run(self.request,'bsa.classified-air-allocation',self.root/'unavailable')
        self.assertEqual(result['execution']['status'],'unavailable')
        self.assertIsNone(result['payload'])
