import copy
import json
from pathlib import Path
import unittest
from bsa.module_thermal import prepare

ROOT=Path(__file__).resolve().parents[1]


class ThermalInheritanceTests(unittest.TestCase):
    def setUp(self):
        self.template=json.loads((ROOT/'examples/thermal-ifc/project.json').read_text())
        self.binding=dict(source='Synthetic explicit mapping and orientation',north_axis_deg=30,spaces=[dict(guid=g,id=n,source='Synthetic identity mapping') for g,n in [('A','ZoneA'),('B','ZoneB')]])
        spaces=[dict(id=g,origin_m=[i*2,0,0],size_m=[2,3,4],floor_area_m2=6) for i,g in enumerate(('A','B'))]
        self.result=dict(execution=dict(status='completed'),payload_schema='bsa.spatial-boxes/1',payload=dict(spaces=spaces,contacts=[dict(spaces=['A','B'],axis=0,area_m2=12)]))

    def test_geometry_identity_and_nongeometry_preserved(self):
        original=copy.deepcopy(self.template);project=prepare(self.result,self.template,self.binding)
        self.assertEqual(self.template,original)
        self.assertEqual(project['building']['spaces'][1]['origin_m'],[2,0,0])
        self.assertEqual(project['building']['north_axis_deg'],30)
        self.assertEqual(project['building']['spaces'][0]['id'],'ZoneA')
        self.assertEqual(project['weather'],original['weather'])

    def test_missing_space_dropped_contact_and_replacement_geometry_reject(self):
        changed=copy.deepcopy(self.binding);changed['spaces'].pop()
        with self.assertRaises(ValueError):prepare(self.result,self.template,changed)
        changed=copy.deepcopy(self.result);changed['payload']['contacts']=[]
        with self.assertRaises(ValueError):prepare(changed,self.template,self.binding)
        changed=copy.deepcopy(self.template);changed['building']['spaces']=[]
        with self.assertRaises(ValueError):prepare(self.result,changed,self.binding)

    def test_unexecuted_geometry_or_invented_orientation_reject(self):
        self.result['execution']['status']='unavailable'
        with self.assertRaises(ValueError):prepare(self.result,self.template,self.binding)
        self.result['execution']['status']='completed';self.binding.pop('north_axis_deg')
        with self.assertRaises(ValueError):prepare(self.result,self.template,self.binding)
