import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.bim import run as author
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.hvac_devices import bind,validate,PSET
from bsa.thermal_binding import extract
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/hvac-equipment'


class HVACDeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        author(EXAMPLE/'bim.json',cls.root/'bim');cls.ifc=cls.root/'bim/model.ifc'
        cls.p=json.loads((EXAMPLE/'project.json').read_text());cls.b=json.loads((EXAMPLE/'binding.json').read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_saved_millimetre_geometry_and_rating_identity(self):
        import ifcopenshell
        from ifcopenshell.util.unit import convert_file_length_units
        before=digest(self.ifc);_,geo=extract(self.ifc,self.b)
        p=copy.deepcopy(self.p);r=bind(self.ifc,p,self.b,geo)
        self.assertEqual(len(r['devices']),3)
        self.assertEqual({z['ifc_device_guid'] for z in p['building']['hvac']['zones']},{r['device_guid'] for r in self.b['hvac_devices']})
        mm=self.root/'millimetres.ifc';convert_file_length_units(ifcopenshell.open(str(self.ifc)),'MILLIMETERS').write(str(mm))
        _,geo_mm=extract(mm,self.b);r_mm=bind(mm,copy.deepcopy(self.p),self.b,geo_mm)
        for original,converted in zip(r['devices'],r_mm['devices']):
            for a,b in zip(sum(original['body_bounds_m'],[]),sum(converted['body_bounds_m'],[])):self.assertAlmostEqual(a,b)
        self.assertEqual(digest(self.ifc),before)

    def test_missing_duplicate_class_and_wrong_space_audit(self):
        import ifcopenshell
        b=copy.deepcopy(self.b);b['hvac_devices'].pop()
        with self.assertRaises(ProjectError):validate(self.p,b)
        b=copy.deepcopy(self.b);b['hvac_devices'][1]['device_guid']=b['hvac_devices'][0]['device_guid']
        with self.assertRaises(ProjectError):validate(self.p,b)
        _,geo=extract(self.ifc,self.b)
        b=copy.deepcopy(self.b);b['hvac_devices'][0]['device_guid']=ifcopenshell.open(str(self.ifc)).by_type('IfcLightFixture')[0].GlobalId
        with self.assertRaisesRegex(ProjectError,'class or type'):bind(self.ifc,copy.deepcopy(self.p),b,geo)
        geo['ifc_sha256']='0'*64
        with self.assertRaisesRegex(ProjectError,'different saved IFC'):bind(self.ifc,copy.deepcopy(self.p),self.b,geo)

    def test_native_rating_container_system_geometry_and_coverage_tampering(self):
        import ifcopenshell
        import ifcopenshell.api as api
        import numpy as np
        for mode in ('rating','container','system','geometry','extra','reserved'):
            model=ifcopenshell.open(str(self.ifc));obj=model.by_guid(self.b['hvac_devices'][0]['device_guid']);group=model.by_guid(self.b['hvac_devices'][0]['system_guid'])
            if mode=='rating':
                pset=next(r.RelatingPropertyDefinition for r in obj.IsDefinedBy if r.is_a('IfcRelDefinesByProperties') and r.RelatingPropertyDefinition.Name=='BSA_DesignInputs')
                api.run('pset.edit_pset',model,pset=pset,properties={'PTAC_CoolingCapacity_thermal_W':3999})
            elif mode=='container':api.run('spatial.assign_container',model,products=[obj],relating_structure=model.by_guid(self.b['spaces'][1]['guid']))
            elif mode=='system':group.PredefinedType='VENTILATION'
            elif mode=='geometry':
                matrix=np.eye(4);matrix[:3,3]=[100,5,2];api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)
            elif mode=='extra':
                extra=api.run('root.copy_class',model,product=obj);api.run('system.assign_system',model,products=[extra],system=group)
            else:api.run('pset.add_pset',model,product=obj,name=PSET)
            path=self.root/(mode+'.ifc');model.write(str(path));_,geo=extract(path,self.b)
            with self.subTest(mode=mode),self.assertRaises(ProjectError):bind(path,copy.deepcopy(self.p),self.b,geo)

    @unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
    def test_actual_bim_annual_property_revision_and_original_entities(self):
        import ifcopenshell
        import ifcopenshell.util.element as element
        import openstudio as sdk
        out=self.root/'workflow';r=execute(ROOT/'examples/hvac-equipment-plan.json',out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertEqual(r['tasks']['thermal']['status'],'pass');self.assertTrue(verify(out)['integrity_pass'])
        self.assertEqual(digest(out/'model/model.ifc'),digest(out/'thermal/model.ifc'))
        original=ifcopenshell.open(str(out/'model/model.ifc'));saved=ifcopenshell.open(str(out/'thermal/analysis.ifc'))
        self.assertTrue(all(str(saved.by_id(e.id()))==str(e) for e in original))
        audit=json.loads((out/'thermal/thermal-binding.json').read_text());self.assertTrue(audit['annotated_ifc']['original_entities_unchanged']);self.assertEqual(audit['annotated_ifc']['schema_issues'],0)
        model=sdk.model.Model.load(sdk.path(str(out/'thermal/annual/baseline/model.osm'))).get()
        for row in self.b['hvac_devices']:
            guid=row['device_guid'];props=element.get_psets(saved.by_guid(guid))[PSET]
            self.assertEqual(props['SourceDeviceGUID'],guid);self.assertEqual(props['SourceIFCSHA256'],digest(out/'model/model.ifc'))
            self.assertEqual(props['AnnualReportSHA256'],digest(out/'thermal/annual/annual.json'))
            self.assertTrue(props['CalculatedChecksPass']);self.assertFalse(props['DesignAccepted'])
            self.assertGreater(props['BaselineAnnualElectricity_kWh'],0)
            unit=model.getZoneHVACPackagedTerminalAirConditionerByName(row['zone_id']+' PTAC').get()
            self.assertEqual(unit.additionalProperties().getFeatureAsString('IFCDeviceGUID').get(),guid)
        from bsa.thermal_hvac import audit as audit_hvac
        p=json.loads((out/'thermal/bound-project.json').read_text())
        model.getZoneHVACPackagedTerminalAirConditioners()[0].additionalProperties().setFeature('IFCDeviceGUID','0'*22)
        with self.assertRaises(ProjectError):audit_hvac(model,p['building']['hvac'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
    def test_actual_failed_capacity_remains_failed_in_derived_ifc(self):
        import ifcopenshell
        import ifcopenshell.util.element as element
        from bsa.thermal_binding import run
        p=copy.deepcopy(self.p);bim=json.loads((EXAMPLE/'bim.json').read_text())
        for zone in p['building']['hvac']['zones']:zone['heating_capacity_w']=1
        for device in bim['devices']:
            if device['ifc_class']=='IfcUnitaryEquipment':device['properties']['PTAC_HeatingCapacity_thermal_W']=1
        project=self.root/'failed-project.json';project.write_text(json.dumps(p),encoding='utf-8')
        geometry=self.root/'failed-bim.json';geometry.write_text(json.dumps(bim),encoding='utf-8')
        author(geometry,self.root/'failed-model')
        out=self.root/'failed-analysis'
        result=run(project,EXAMPLE/'binding.json',self.root/'failed-model/model.ifc',ROOT/'examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz',out,Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertFalse(result['calculated_checks_pass'])
        model=ifcopenshell.open(str(out/'analysis.ifc'))
        for row in self.b['hvac_devices']:
            props=element.get_psets(model.by_guid(row['device_guid']))[PSET]
            self.assertFalse(props['CalculatedChecksPass']);self.assertFalse(props['DesignAccepted'])
