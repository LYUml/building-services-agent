import calendar
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from bsa.annual_energy import RATES,UNMET,validate,read_weather,weather_bytes,run,extract
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/annual-energy'
WEATHER=EXAMPLE/'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz'


def project():return json.loads((EXAMPLE/'project.json').read_text())


class AnnualInputTests(unittest.TestCase):
    def test_repeated_site_missing_sources_and_invalid_budgets_rejected(self):
        for change in (lambda p:p['building'].update(site={}),lambda p:p['building'].update(design_days=[]),
                       lambda p:p.update(calendar_year=True),lambda p:p['weather'].update(sha256='0'),
                       lambda p:p['solver'].update(max_runtime_s=False),lambda p:p['targets'].update(maximum_zone_unmet_hours=-1)):
            p=project();change(p)
            with self.assertRaises(ProjectError):validate(p)

    def test_packaged_weather_bytes_identity_calendar_and_missing_fields(self):
        p=project();r=read_weather(WEATHER,p['weather'],2025)
        self.assertEqual(r['hours'],8760);self.assertEqual(r['station_id'],'725300')
        self.assertAlmostEqual(r['site']['latitude_deg'],41.98)
        self.assertNotEqual(r['source_years'],[2025])
        original=weather_bytes(WEATHER).decode();lines=original.splitlines()
        for change in ('duplicate_hour','missing_hour','missing_dry_bulb','wrong_station','wrong_hash'):
            rows=lines[:];config=copy.deepcopy(p['weather'])
            if change=='duplicate_hour':rows[9]=rows[8]
            elif change=='missing_hour':rows.pop()
            elif change=='missing_dry_bulb':values=rows[8].split(',');values[6]='99.9';rows[8]=','.join(values)
            elif change=='wrong_station':config['station_id']='unknown'
            raw=('\n'.join(rows)+'\n').encode();config['sha256']=hashlib.sha256(raw).hexdigest() if change!='wrong_hash' else '0'*64
            with tempfile.TemporaryDirectory() as f:
                path=Path(f)/'weather.epw';path.write_bytes(raw)
                with self.subTest(change=change),self.assertRaises(ProjectError):read_weather(path,config,2025)

    def test_complete_leap_calendar_requires_explicit_weather_permission(self):
        p=project();lines=weather_bytes(WEATHER).decode().splitlines();headers=lines[:8];data=lines[8:];extra=[]
        for line in data:
            values=line.split(',')
            if values[1:3]==['2','28']:values[0]='2024';values[2]='29';extra.append(','.join(values))
        index=next(i for i,line in enumerate(data) if line.split(',')[1:3]==['3','1']);data[index:index]=extra
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'leap.epw';raw=('\n'.join(headers+data)+'\n').encode();path.write_bytes(raw);config=dict(p['weather'],sha256=hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(ProjectError,'allows leap'):read_weather(path,config,2024)
            headers[4]=headers[4].replace(',No,',',Yes,',1);raw=('\n'.join(headers+data)+'\n').encode();path.write_bytes(raw);config['sha256']=hashlib.sha256(raw).hexdigest()
            self.assertEqual(read_weather(path,config,2024)['hours'],8784)


@unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
class AnnualEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        cls.result=run(EXAMPLE/'project.json',WEATHER,cls.root/'annual',Path(os.environ['BSA_TEST_ENERGYPLUS']))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_actual_8760_hours_and_independent_monthly_lighting_balance(self):
        r=self.result;self.assertTrue(r['calculated_checks_pass']);self.assertFalse(r['design_accepted'])
        self.assertTrue(r['inputs_unchanged']);self.assertEqual(r['weather']['hours'],8760)
        self.assertEqual(digest(self.root/'annual/weather.epw'),r['source_data']['weather']['sha256'])
        for kind,kw in [('baseline',.48),('variant',.24)]:
            summary=r['results'][kind]['summary'];self.assertEqual(r['results'][kind]['metadata']['design_day_count'],0)
            self.assertEqual(summary['environments'][0][2],3)
            for row in summary['annual']:self.assertEqual(row['hours'],8760)
            lights=next(v for v in summary['annual'] if v['variable']==RATES[2]);self.assertAlmostEqual(lights['annual_kwh'],kw*8760,places=6)
            for month in (1,2,12):
                row=next(v for v in summary['monthly'] if v['month']==month and v['variable']==RATES[2])
                self.assertAlmostEqual(row['kwh'],kw*24*calendar.monthrange(2025,month)[1],places=6)
            c=sqlite3.connect(str(self.root/'annual'/kind/'eplusout.sql'));flags=c.execute('SELECT Completed,CompletedSuccessfully FROM Simulations').fetchall();c.close()
            self.assertEqual(summary['sql_completion_flags'],[list(row) for row in flags])
            self.assertTrue(r['results'][kind]['engine_success_evidence']['stdout_success_marker'])
            self.assertTrue(r['results'][kind]['completion']['completion_verified'])
            self.assertEqual(r['results'][kind]['completion']['sql_flags_raw'],list(flags[0]))
        self.assertLess(r['comparison'][0]['change_kwh'],0);self.assertGreater(r['comparison'][1]['change_kwh'],0)
        self.assertAlmostEqual(r['comparison'][2]['change_kwh'],-2102.4)

    def test_truncated_wrong_interval_and_wrong_environment_sql_rejected(self):
        p=project();source=self.root/'annual/baseline/eplusout.sql';before=digest(source)
        with tempfile.TemporaryDirectory() as f:
            folder=Path(f)/'annual # source';folder.mkdir();path=folder/'copied.sql';shutil.copyfile(source,path)
            summary,_=extract(path,2025,12,40,p['solver'],p['targets'])
            self.assertTrue(summary['calculated_checks_pass']);self.assertEqual(list(Path(f).iterdir()),[folder])
        for command in ('DELETE FROM ReportData WHERE ReportDataIndex=(SELECT MIN(ReportDataIndex) FROM ReportData)',
                        'UPDATE Time SET Interval=30 WHERE TimeIndex=(SELECT MIN(TimeIndex) FROM Time)',
                        'UPDATE EnvironmentPeriods SET EnvironmentType=1'):
            with tempfile.TemporaryDirectory() as f:
                path=Path(f)/'changed.sql';shutil.copyfile(source,path);c=sqlite3.connect(path);c.execute(command);c.commit();c.close()
                with self.assertRaises(ProjectError):extract(path,2025,12,40,p['solver'],p['targets'])
        self.assertEqual(digest(source),before)

    def test_explicit_failed_unmet_target_is_not_turned_into_a_pass(self):
        p=project();source=self.root/'annual/baseline/eplusout.sql'
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'changed.sql';shutil.copyfile(source,path);c=sqlite3.connect(path)
            c.execute('''UPDATE ReportData SET Value=1 WHERE ReportDataIndex=(SELECT MIN(r.ReportDataIndex) FROM ReportData r JOIN ReportDataDictionary d ON r.ReportDataDictionaryIndex=d.ReportDataDictionaryIndex WHERE d.Name=?)''',(UNMET[0],));c.commit();c.close()
            summary,_=extract(path,2025,12,40,p['solver'],dict(p['targets'],maximum_zone_unmet_hours=0))
            self.assertFalse(summary['checks']['zone_unmet_time_target']);self.assertFalse(summary['calculated_checks_pass'])

    def test_workflow_and_weather_asset_integrity(self):
        from bsa.workflow import execute,verify
        out=self.root/'workflow';r=execute(EXAMPLE/'plan.json',out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertTrue(r['execution_pass']);self.assertTrue(verify(out)['integrity_pass'])
        (out/'annual/baseline/hourly-building-rates.csv').write_text('tampered')
        self.assertFalse(verify(out)['integrity_pass'])

    def test_actual_leap_calendar_with_explicit_synthetic_weather_derivative(self):
        p=project();lines=weather_bytes(WEATHER).decode().splitlines();headers=lines[:8];data=lines[8:];extra=[]
        for line in data:
            fields=line.split(',')
            if fields[1:3]==['2','28']:fields[0]='2024';fields[2]='29';extra.append(','.join(fields))
        index=next(i for i,line in enumerate(data) if line.split(',')[1:3]==['3','1']);data[index:index]=extra
        headers[4]=headers[4].replace(',No,',',Yes,',1)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as f:
            root=Path(f);weather=root/'synthetic-leap.epw';raw=('\n'.join(headers+data)+'\n').encode();weather.write_bytes(raw)
            p.update(calendar_year=2024);p['weather'].update(sha256=hashlib.sha256(raw).hexdigest(),source='Synthetic leap test: unmodified Chicago hourly values with Feb28 duplicated as Feb29 and explicit leap permission; not a real meteorological leap dataset')
            path=root/'project.json';path.write_text(json.dumps(p));r=run(path,weather,root/'run',Path(os.environ['BSA_TEST_ENERGYPLUS']))
            self.assertTrue(r['calculated_checks_pass']);self.assertEqual(r['weather']['hours'],8784)
            lights=next(row for row in r['results']['baseline']['summary']['annual'] if row['variable']==RATES[2])
            self.assertAlmostEqual(lights['annual_kwh'],.48*8784,places=6)
