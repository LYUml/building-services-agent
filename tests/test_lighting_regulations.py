import copy
import json
from pathlib import Path
import unittest
from bsa.engine import ProjectError
from bsa.lighting_regulations import prepare

ROOT=Path(__file__).resolve().parents[1]


class LightingBindingTests(unittest.TestCase):
    def setUp(self):
        self.e=json.loads((ROOT/'examples/office-electrical/project.json').read_text())
        self.g=json.loads((ROOT/'examples/office-electrical/geometry.json').read_text())
        self.b=json.loads((ROOT/'examples/regulations-hk-lighting/shared-space-basis.json').read_text())

    def test_area_and_power_derive_from_shared_sources_without_demand_factor(self):
        self.e['circuits'][0]['demand_factor']=.1
        result,omitted=prepare(self.e,self.g,self.b);space=result['Office']['lighting_space']
        self.assertEqual(space['internal_floor_area']['value'],48)
        self.assertEqual(sum(d['full_output_circuit_power']['value'] for d in space['luminaires']),120)
        self.assertEqual(omitted,[])
        self.e['devices'][0]['electrical_kw']=.1
        updated,_=prepare(self.e,self.g,self.b)
        self.assertEqual(sum(d['full_output_circuit_power']['value'] for d in updated['Office']['lighting_space']['luminaires']),180)

    def test_missing_envelope_or_space_basis_cannot_drop_fixture(self):
        for target in ('geometry','basis'):
            g=copy.deepcopy(self.g);b=copy.deepcopy(self.b)
            if target=='geometry':g['devices'].pop()
            else:b={}
            with self.subTest(target=target),self.assertRaises(ProjectError):prepare(self.e,g,b)

    def test_separate_rooms_keep_individual_areas_and_inventory(self):
        self.g['spaces'][0]['size_m'][0]=3
        self.g['spaces'].append(dict(id='Office2',origin_m=[3,0,0],size_m=[5,6,3],source='geometry'))
        for d in self.g['devices'][1:]:d['space']='Office2'
        self.b['Office2']=copy.deepcopy(self.b['Office'])
        r,_=prepare(self.e,self.g,self.b)
        self.assertEqual(r['Office']['lighting_space']['internal_floor_area']['value'],18)
        self.assertEqual(r['Office2']['lighting_space']['internal_floor_area']['value'],30)
        self.assertEqual([d['id'] for d in r['Office2']['lighting_space']['luminaires']],['L2','L3'])

    def test_power_override_rejected_and_nonlight_identity_reported(self):
        self.b['Office']['lighting_space']={}
        with self.assertRaisesRegex(ProjectError,'must not repeat'):prepare(self.e,self.g,self.b)
        del self.b['Office']['lighting_space'];self.g['devices'][0]['ifc_class']='IfcOutlet'
        r,omitted=prepare(self.e,self.g,self.b)
        self.assertEqual(omitted[0]['id'],'L1')
        self.assertEqual(len(r['Office']['lighting_space']['luminaires']),2)
