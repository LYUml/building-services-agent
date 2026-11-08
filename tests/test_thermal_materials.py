import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.annual_energy import validate
from bsa.energy import build
from bsa.engine import ProjectError
from bsa.thermal_materials import audit
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/thermal-materials/project.json'


def fixture():
    p=json.loads(PROJECT.read_text())['building']
    p.update(spaces=[dict(id='Lower',source='Synthetic box',origin_m=[0,0,0],size_m=[4,3,3]),dict(id='Upper',source='Synthetic box',origin_m=[0,0,3],size_m=[4,3,3])],site=dict(latitude_deg=0,longitude_deg=0,timezone_h=0,elevation_m=0),design_days=[])
    return p


class ThermalMaterialTests(unittest.TestCase):
    def test_invalid_properties_and_ambiguous_sources(self):
        p=json.loads(PROJECT.read_text());p['building']['spaces']=fixture()['spaces']
        validate(p)
        for key,value in [('source',''),('roughness',[]),('thickness_m',0),('conductivity_w_mk',-1),('density_kg_m3',float('nan')),('specific_heat_j_kgk',99),('thermal_absorptance',1),('solar_absorptance',1.01),('visible_absorptance',False)]:
            q=copy.deepcopy(p);q['building']['opaque_constructions']['roof']['layers'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ProjectError):validate(q)
        q=copy.deepcopy(p);q['building']['envelope_r_m2k_w']=2
        with self.assertRaises(ProjectError):validate(q)
        q=copy.deepcopy(p);q['building']['opaque_constructions'].pop('floor')
        with self.assertRaises(ProjectError):validate(q)
        q=copy.deepcopy(p);q['building']['opaque_constructions']['roof']['layers'][1]['resistance_m2k_w']=.0001
        with self.assertRaises(ProjectError):validate(q)

    def test_saved_layers_area_capacity_and_stacked_reverse_order(self):
        import openstudio as sdk
        p=fixture()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            r=build(p,12,Path(folder));a=r['material_audit']
            self.assertTrue(a['saved_layer_properties_match'])
            self.assertAlmostEqual(a['assemblies']['exterior_wall']['layer_resistance_m2k_w'],2.3)
            self.assertAlmostEqual(a['assemblies']['roof']['layer_conductance_w_m2k'],1/3.2)
            self.assertEqual(a['assemblies']['interzone']['areal_heat_capacity_j_m2k'],111500)
            self.assertEqual(a['role_area_m2'],dict(exterior_wall=84,roof=12,floor=12,interzone=24))
            shared=[s for s in a['surfaces'] if s['role']=='interzone']
            self.assertEqual({s['surface_type'] for s in shared},{'Floor','RoofCeiling'})
            self.assertEqual(sum(s['reversed_layers'] for s in shared),1)
            model=sdk.model.Model.load(sdk.path(str(Path(folder)/'model.osm'))).get()
            for surface in model.getSurfaces():
                if surface.outsideBoundaryCondition()!='Surface':continue
                layers=surface.construction().get().to_Construction().get().layers()
                names=[l.additionalProperties().getFeatureAsString('InputName').get() for l in layers]
                self.assertEqual(names,['First face finish','Partition core','Second face finish'] if surface.space().get().thermalZone().get().nameString()=='Lower' else ['Second face finish','Partition core','First face finish'])

    def test_saved_property_order_and_source_tampering_rejected(self):
        import openstudio as sdk
        p=fixture()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            build(p,12,Path(folder));path=sdk.path(str(Path(folder)/'model.osm'))
            for mode in ('property','order','source'):
                model=sdk.model.Model.load(path).get()
                construction=model.getConstructionByName('BSA exterior_wall').get()
                if mode=='property':construction.layers()[0].to_StandardOpaqueMaterial().get().setThickness(.11)
                elif mode=='source':construction.layers()[0].additionalProperties().setFeature('Source','Wrong source')
                else:
                    vector=sdk.model.MaterialVector()
                    for m in reversed(construction.layers()):vector.append(m)
                    construction.setLayers(vector)
                with self.subTest(mode=mode),self.assertRaises(ProjectError):audit(model,p['opaque_constructions'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
    def test_saved_ifc_layered_annual_engine(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'run'
            result=execute(ROOT/'examples/thermal-materials-plan.json',out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']))
            self.assertEqual(result['tasks']['thermal']['status'],'pass')
            self.assertTrue(verify(out)['integrity_pass'])
            annual=json.loads((out/'thermal/annual/annual.json').read_text())
            for case in annual['results'].values():
                a=case['metadata']['material_audit']
                self.assertTrue(a['saved_layer_properties_match'])
                self.assertEqual(a['role_area_m2'],dict(exterior_wall=138,roof=102,floor=102,interzone=72))
                self.assertEqual(case['metadata']['thermal_zones'],3)
                self.assertEqual(case['metadata']['translation_warnings'],[])
                self.assertTrue(case['summary']['calculated_checks_pass'])
            self.assertFalse(annual['design_accepted'])
