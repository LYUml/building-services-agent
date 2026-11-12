import copy
import json
from pathlib import Path
import unittest
from bsa.spatial_lighting_rules import prepare
from bsa.regulations import evaluate

ROOT=Path(__file__).resolve().parents[1]


class SpatialLightingRulesTests(unittest.TestCase):
    def setUp(self):
        self.pack=json.loads((ROOT/'regulations/hk/lighting-2026.11.08/pack.json').read_text())
        self.basis=json.loads((ROOT/'examples/regulations-hk-lighting/project.json').read_text())
        self.basis['lighting_space'].pop('internal_floor_area')
        self.bases={'Room':self.basis}
        self.result=dict(execution=dict(status='completed'),payload_schema='bsa.spatial-boxes/1',payload=dict(spaces=[dict(id='Room',floor_area_m2=48)]))

    def test_area_inherited_and_watts_unchanged(self):
        projects=prepare(self.result,self.bases,self.pack)
        self.assertEqual(projects['Room']['lighting_space']['internal_floor_area']['value'],48)
        self.assertEqual(projects['Room']['lighting_space']['luminaires'],self.basis['lighting_space']['luminaires'])
        self.assertNotIn('internal_floor_area',self.basis['lighting_space'])

    def test_polygon_space_area_inherited_without_box_dimensions(self):
        self.result['payload_schema']='bsa.spatial-polygons/1'
        self.result['payload']=dict(schema='bsa.spatial-polygons/1',coordinate_frame=dict(id='declared',kind='source-world-si',length_unit='m',georeferenced=False),units=dict(length='m',area='m2'),point_grid_m=1e-9,source_geometry_matches=True,simulation_ready=False,design_accepted=False,
            spaces=[dict(id='Room',recognized_id='native-id',boundary_vertices=[[0,0],[5,0],[5,2],[2,2],[2,4],[0,4],[0,0]],floor_area_m2=14,height_m=3,floor_elevation_m=0)])
        project=prepare(self.result,self.bases,self.pack)['Room']
        self.assertEqual(project['lighting_space']['internal_floor_area']['value'],14)
        self.result['payload']['spaces'][0]['floor_area_m2']=100
        with self.assertRaisesRegex(ValueError,'Polygon area'):prepare(self.result,self.bases,self.pack)

    def test_dropped_room_and_area_override_reject(self):
        with self.assertRaises(ValueError):prepare(self.result,{},self.pack)
        self.basis['lighting_space']['internal_floor_area']={'value':10000,'unit':'m2','source':'Untrusted replacement'}
        with self.assertRaisesRegex(ValueError,'replace inherited area'):prepare(self.result,self.bases,self.pack)

    def test_repeated_luminaire_identity_or_wrong_jurisdiction_reject(self):
        self.result['payload']['spaces'].append(dict(id='Other',floor_area_m2=20));self.bases['Other']=copy.deepcopy(self.basis)
        with self.assertRaisesRegex(ValueError,'Unique luminaire'):prepare(self.result,self.bases,self.pack)
        self.result['payload']['spaces'].pop();self.bases.pop('Other');self.basis['jurisdiction']='Other'
        with self.assertRaisesRegex(ValueError,'matching jurisdiction'):prepare(self.result,self.bases,self.pack)

    def test_source_absence_stays_pending_and_unexecuted_space_rejects(self):
        project=prepare(self.result,self.bases,self.pack)['Room']
        result=evaluate(self.pack,project,ROOT/'runs/nonexistent-rule-cache')
        self.assertFalse(result['supported_checks_pass']);self.assertEqual(result['checks'][0]['status'],'pending')
        self.result['execution']['status']='unavailable'
        with self.assertRaises(ValueError):prepare(self.result,self.bases,self.pack)
