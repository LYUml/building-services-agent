from contextlib import closing
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.thermal_hvac import validate,extrema,audit,extract,RATES
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/thermal-ptac/project.json'


class PTACInputTests(unittest.TestCase):
    def test_bad_ratings_curves_and_identity(self):
        hvac=json.loads(PROJECT.read_text())['building']['hvac'];spaces=[{'id':s['id']} for s in hvac['zones']];validate(hvac,spaces)
        for field,value in [('cooling_capacity_w',0),('cooling_cop',False),('cooling_shr',.4),('fan_efficiency',1.1),('motor_efficiency',float('nan')),('heating_capacity_w',-1)]:
            q=copy.deepcopy(hvac);q['zones'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ProjectError):validate(q,spaces)
        q=copy.deepcopy(hvac);q['zones'][1]['id']='Office'
        with self.assertRaises(ProjectError):validate(q,spaces)
        q=copy.deepcopy(hvac);q['curves']['eir_flow']['source']=''
        with self.assertRaises(ProjectError):validate(q,spaces)
        q=copy.deepcopy(hvac);q['curves']['part_load']['coefficients']=[.8,0,0]
        with self.assertRaisesRegex(ProjectError,'full load'):validate(q,spaces)

    def test_full_domain_extrema_not_just_positive_corners(self):
        # (x-.5)^2+(y-.5)^2-.1: all corners positive, interior negative.
        low,high=extrema([.4,-1,1,-1,1,0],[0,1],[0,1])
        self.assertAlmostEqual(low,-.1);self.assertAlmostEqual(high,.4)
        hvac=json.loads(PROJECT.read_text())['building']['hvac']
        hvac['curves']['capacity_temperature'].update(coefficients=[.4,-1,1,-1,1,0],x_range=[0,1],y_range=[0,1])
        with self.assertRaisesRegex(ProjectError,'full input domain'):validate(hvac,[{'id':s['id']} for s in hvac['zones']])
        self.assertLess(extrema([v*1e-200 for v in [.4,-1,1,-1,1,0]],[0,1],[0,1])[0],0)


@unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
class PTACEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name);cls.out=cls.root/'workflow'
        cls.result=execute(ROOT/'examples/thermal-ptac-plan.json',cls.out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']))
        if cls.result['tasks']['thermal']['status']!='pass':raise AssertionError(cls.result['tasks']['thermal'])
        cls.annual=json.loads((cls.out/'thermal/annual/annual.json').read_text());cls.p=cls.annual['source_data'];cls.base=cls.annual['results']['baseline']

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_actual_equipment_electricity_topology_and_coverage(self):
        self.assertTrue(verify(self.out)['integrity_pass'])
        self.assertTrue(self.base['metadata']['hvac_audit']['saved_hvac_matches'])
        self.assertEqual(len(self.base['metadata']['hvac_audit']['records']),3)
        self.assertTrue(all(self.base['summary']['hvac']['checks'].values()))
        total=next(r for r in self.base['summary']['annual'] if r['variable']==RATES[3])['annual_kwh']
        self.assertAlmostEqual(total,sum(r['ptac_electricity_kwh'] for r in self.base['summary']['hvac']['zones']))
        self.assertGreater(total,0)
        for key in ('cooling_electricity_kwh','heating_electricity_kwh','fan_electricity_kwh'):self.assertGreater(sum(r[key] for r in self.base['summary']['hvac']['zones']),0)
        idf=(self.out/'thermal/annual/baseline/model.idf').read_text()
        self.assertNotIn('ZoneHVAC:IdealLoadsAirSystem,',idf)
        self.assertNotIn('Schedule Type Limits Name is empty',self.base['diagnostics'])
        self.assertFalse(self.annual['design_accepted'])

    def test_saved_capacity_curve_link_source_and_mode_tampering(self):
        import openstudio as sdk
        path=sdk.path(str(self.out/'thermal/annual/baseline/model.osm'))
        for mode in ('capacity','curve','source','mode','ideal'):
            model=sdk.model.Model.load(path).get();unit=model.getZoneHVACPackagedTerminalAirConditioners()[0]
            coil=unit.coolingCoil().to_CoilCoolingDXSingleSpeed().get()
            if mode=='capacity':coil.setRatedTotalCoolingCapacity(1234)
            elif mode=='curve':coil.setEnergyInputRatioFunctionOfTemperatureCurve(model.getCurveBiquadraticByName('BSA DX capacity_temperature').get())
            elif mode=='source':unit.additionalProperties().setFeature('Source','Wrong source')
            elif mode=='mode':unit.supplyAirFanOperatingModeSchedule().to_ScheduleConstant().get().setValue(1)
            else:unit.thermalZone().get().setUseIdealAirLoads(True)
            with self.subTest(mode=mode),self.assertRaises(ProjectError):audit(model,self.p['building']['hvac'])

    def test_native_component_sum_tamper_and_missing_series(self):
        for mode in ('sum','missing'):
            sql=self.root/(mode+' # PTAC.sql');shutil.copyfile(self.out/'thermal/annual/baseline/eplusout.sql',sql)
            with closing(sqlite3.connect(sql)) as con:
                if mode=='sum':con.execute("UPDATE ReportData SET Value=Value+1 WHERE ReportDataDictionaryIndex IN (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary WHERE Name='Cooling Coil Electricity Rate' AND KeyValue='OFFICE PTAC DX')")
                else:con.execute("DELETE FROM ReportData WHERE ReportDataDictionaryIndex IN (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary WHERE Name='Fan Electricity Rate' AND KeyValue='OFFICE PTAC FAN')")
                con.commit()
            if mode=='sum':
                result=extract(sql,self.p['building']['hvac'],self.base['metadata'],2025,self.p['solver'])
                self.assertFalse(result['checks']['hourly_electricity_sum']);self.assertFalse(result['calculated_checks_pass'])
            else:
                with self.assertRaises(ProjectError):extract(sql,self.p['building']['hvac'],self.base['metadata'],2025,self.p['solver'])

    def test_undersized_heating_retains_failed_unmet_target(self):
        from bsa.annual_energy import run
        p=copy.deepcopy(self.p)
        for zone in p['building']['hvac']['zones']:zone['heating_capacity_w']=1
        project=self.root/'undersized.json';project.write_text(json.dumps(p),encoding='utf-8')
        r=run(project,self.out/'thermal/annual/weather.epw',self.root/'undersized',Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertFalse(r['calculated_checks_pass'])
        self.assertTrue(r['results']['baseline']['completion']['completion_verified'])
        self.assertFalse(r['results']['baseline']['summary']['checks']['zone_unmet_time_target'])
        self.assertFalse(r['design_accepted'])
