from contextlib import closing
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.thermal_operation import validate,fractions,audit,extract,DAYS
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/thermal-operation/project.json'


class OperationInputTests(unittest.TestCase):
    def test_bad_profiles_sources_and_physics(self):
        p=json.loads(PROJECT.read_text())['building']['operation'];validate(p)
        for group,key,value in [('lighting','source',''),('equipment','fraction_lost',.8),('people','activity_w_per_person',0),('people','sensible_heat_fraction',1.1),('infiltration','air_changes_per_hour',True),('ventilation','fan_total_efficiency',0),('ventilation','type','Imagined')]:
            q=copy.deepcopy(p);q[group][key]=value
            with self.subTest(group=group,key=key),self.assertRaises(ProjectError):validate(q)
        for values in ([0]*23,[0]*23+[float('nan')],[0]*23+[1.01]):
            q=copy.deepcopy(p);q['lighting']['weekly_fraction']['monday']=values
            with self.assertRaises(ProjectError):validate(q)
        q=copy.deepcopy(p);q['equipment']['weekly_fraction'].pop('sunday')
        with self.assertRaises(ProjectError):validate(q)

    def test_independent_calendar_and_leap_integrals(self):
        weekly=json.loads(PROJECT.read_text())['building']['operation']['lighting']['weekly_fraction']
        # 2025: 261 weekdays + 52 Saturdays at two equivalent full-load hours.
        values=fractions(weekly,2025)
        self.assertEqual(len(values),8760);self.assertEqual(sum(values),261*10+52*2)
        # 2024: 262 weekdays, 52 Saturdays; Feb 29 Thursday is retained.
        leap=fractions(weekly,2024)
        self.assertEqual(len(leap),8784);self.assertEqual(sum(leap),262*10+52*2)
        distinct={d:[i/10]*24 for i,d in enumerate(DAYS)}
        self.assertEqual(fractions(distinct,2025)[:24],[.2]*24)  # Wednesday, not EPW weekday header.


@unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
class OperationEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name);cls.out=cls.root/'workflow'
        cls.result=execute(ROOT/'examples/thermal-operation-plan.json',cls.out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']))
        if cls.result['tasks']['thermal']['status']!='pass':raise AssertionError(cls.result['tasks']['thermal'])
        cls.annual=json.loads((cls.out/'thermal/annual/annual.json').read_text())
        cls.p=cls.annual['source_data'];cls.base=cls.annual['results']['baseline']

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_actual_annual_independent_integrals_and_saved_audit(self):
        self.assertTrue(verify(self.out)['integrity_pass'])
        self.assertAlmostEqual(self.base['summary']['analytic_lighting_kwh'],3321.936)
        op=self.base['summary']['operation']
        totals={r['variable']:r['annual_integral'] for r in op['annual']}
        self.assertAlmostEqual(totals['Electric Equipment Electricity Rate'],2214.624)
        self.assertAlmostEqual(totals['Zone People Occupant Count'],22146.24)
        self.assertAlmostEqual(totals['Zone Ventilation Fan Electricity Energy'],69.207)
        self.assertGreater(totals['Zone Infiltration Mass Flow Rate'],0)
        self.assertTrue(self.base['metadata']['operation_audit']['saved_operation_matches'])
        self.assertEqual(len(self.base['metadata']['operation_audit']['records']),15)
        self.assertTrue(op['calculated_checks_pass']);self.assertFalse(self.annual['design_accepted'])

    def test_hourly_tampering_despite_unchanged_annual_equipment_total(self):
        sql=self.root/'profile # tamper.sql';shutil.copyfile(self.out/'thermal/annual/baseline/eplusout.sql',sql)
        with closing(sqlite3.connect(sql)) as con:
            for hour,delta in ((1,1),(10,-1)):
                ti=con.execute('SELECT TimeIndex FROM Time WHERE Year=2025 AND Month=1 AND Day=1 AND Hour=? AND COALESCE(WarmupFlag,0)=0',(hour,)).fetchone()[0]
                con.execute("UPDATE ReportData SET Value=Value+? WHERE TimeIndex=? AND ReportDataDictionaryIndex IN (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary WHERE Name='Electric Equipment Electricity Rate' AND KeyValue='OFFICE EQUIPMENT')",(delta,ti))
            con.commit()
        summary,_=extract(sql,self.p['building']['operation'],self.base['metadata'],2025,self.p['solver'])
        self.assertTrue(summary['checks']['equipment_annual_integral'])
        self.assertFalse(summary['checks']['equipment_hourly_balance'])
        self.assertFalse(summary['checks']['equipment_per_zone_hourly_balance'])
        self.assertFalse(summary['calculated_checks_pass'])

    def test_saved_weekday_link_property_and_source_changes_rejected(self):
        import openstudio as sdk
        path=sdk.path(str(self.out/'thermal/annual/baseline/model.osm'))
        for mode in ('profile','people','fan','source'):
            model=sdk.model.Model.load(path).get()
            if mode=='profile':
                rules=model.getScheduleRulesetByName('BSA lighting weekly').get().scheduleRules()
                day=next(r.daySchedule() for r in rules if r.applyTuesday());day.clearValues();day.addValue(sdk.Time(0,24,0,0),0)
            elif mode=='people':model.getPeopleDefinitions()[0].setPeopleperSpaceFloorArea(.9)
            elif mode=='fan':model.getZoneVentilationDesignFlowRates()[0].setFanPressureRise(999)
            else:model.getElectricEquipments()[0].additionalProperties().setFeature('Source','Wrong source')
            with self.subTest(mode=mode),self.assertRaises(ProjectError):audit(model,self.p['building']['operation'])

    def test_missing_wrong_units_and_extra_series_rejected(self):
        for mode in ('missing','units','key'):
            sql=self.root/(mode+'.sql');shutil.copyfile(self.out/'thermal/annual/baseline/eplusout.sql',sql)
            with closing(sqlite3.connect(sql)) as con:
                if mode=='missing':con.execute('DELETE FROM ReportData WHERE ReportDataIndex=(SELECT MIN(ReportDataIndex) FROM ReportData WHERE ReportDataDictionaryIndex IN (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary WHERE Name=\'Zone People Occupant Count\'))')
                elif mode=='units':con.execute("UPDATE ReportDataDictionary SET Units='kW' WHERE Name='Electric Equipment Electricity Rate'")
                else:con.execute("UPDATE ReportDataDictionary SET KeyValue='EXTRA' WHERE Name='Zone Ventilation Fan Electricity Energy' AND KeyValue='OFFICE'")
                con.commit()
            with self.subTest(mode=mode),self.assertRaises(ProjectError):extract(sql,self.p['building']['operation'],self.base['metadata'],2025,self.p['solver'])

    def test_zero_loads_and_natural_no_fan_are_actual_zero_series(self):
        from bsa.annual_energy import run
        p=copy.deepcopy(self.p);op=p['building']['operation']
        p['building']['baseline_lighting_w_m2']=p['building']['variant_lighting_w_m2']=0
        op['equipment']['watts_per_m2']=0;op['people']['people_per_m2']=0
        op['infiltration']['air_changes_per_hour']=0
        op['ventilation'].update(type='Natural',fan_pressure_rise_pa=0,flow_m3_s_per_m2=0)
        project=self.root/'zero.json';project.write_text(json.dumps(p),encoding='utf-8')
        r=run(project,self.out/'thermal/annual/weather.epw',self.root/'zero',Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertTrue(r['calculated_checks_pass'])
        self.assertTrue(all(row['annual_integral']==0 for row in r['results']['baseline']['summary']['operation']['annual']))

    def test_actual_leap_weekday_mapping_with_declared_weather_derivative(self):
        from bsa.annual_energy import run
        p=copy.deepcopy(self.p);p['calendar_year']=2024
        rows=list(csv.reader(io.StringIO((self.out/'thermal/annual/weather.epw').read_text())))
        rows[4][1]='Yes';data=[]
        for row in rows[8:]:
            row[0]='2024';data.append(row)
            if row[1:4]==['2','28','24']:
                extra=copy.deepcopy(data[-24:])
                for copied in extra:copied[2]='29'
                data.extend(extra)
        stream=io.StringIO(newline='');csv.writer(stream).writerows(rows[:8]+data)
        raw=stream.getvalue().encode('utf-8');weather=self.root/'synthetic-leap.epw';weather.write_bytes(raw)
        p['weather'].update(sha256=hashlib.sha256(raw).hexdigest(),source='Synthetic calendar derivative; copied February 28 into February 29 for integration testing, not actual weather')
        project=self.root/'leap.json';project.write_text(json.dumps(p),encoding='utf-8')
        r=run(project,weather,self.root/'leap',Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertTrue(r['calculated_checks_pass'])
        self.assertAlmostEqual(r['results']['baseline']['summary']['analytic_lighting_kwh'],102*12*(262*10+52*2)/1000)
