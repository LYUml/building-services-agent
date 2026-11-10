import copy
import csv
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from bsa.climate_context import run
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];PYTHON=ROOT/'tools/honeybee-scene-runtime/Scripts/python.exe'
WEATHER=ROOT/'examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz';BASIS=ROOT/'benchmarks/mit-4401-2018/climate-decisions.json'

@unittest.skipUnless(PYTHON.is_file(),'requires pinned isolated Ladybug runtime')
class ClimateContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.result=run(WEATHER,BASIS,cls.root/'positive',PYTHON)

    def test_actual_source_months_and_irradiation_units_reconcile(self):
        r=self.result
        self.assertEqual(r['source_record_count'],8760);self.assertEqual(sum(m['hours'] for m in r['monthly']),8760)
        self.assertEqual(r['weather_metadata']['station_id'],'725300')
        self.assertEqual(r['weather_metadata']['site']['latitude_deg'],41.98)
        self.assertAlmostEqual(r['annual_irradiation_kwh_m2']['ghi_kwh_m2'],1406.646)
        self.assertAlmostEqual(r['monthly'][0]['dry_bulb_mean_c'],-4.646505376344086)
        self.assertEqual(r['monthly'][1]['hours'],672)
        self.assertTrue(r['hourly_alignment_pass']);self.assertTrue(r['climate_checks_pass'])
        self.assertFalse(r['site_selected']);self.assertFalse(r['shading_calculated']);self.assertFalse(r['design_accepted'])
        self.assertNotEqual(r['weather_metadata']['source_years'],[2025])

    def test_sun_clock_has_exact_midpoints_and_seasonal_physical_sanity(self):
        with (self.root/'positive/ladybug/sun-hourly.csv').open(encoding='utf-8') as file:rows=list(csv.DictReader(file))
        self.assertEqual(rows[0]['local_standard_interval_midpoint'],'2025-01-01T00:30:00')
        self.assertEqual(rows[-1]['local_standard_interval_midpoint'],'2025-12-31T23:30:00')
        with (self.root/'positive/ladybug/sun-seasonal.csv').open(encoding='utf-8') as file:rows=list(csv.DictReader(file))
        june=next(r for r in rows if r['local_standard_time']=='2025-06-21T12:00:00')
        winter=next(r for r in rows if r['local_standard_time']=='2025-12-21T12:00:00')
        # Broad independent latitude/solstice sanity, not ephemeris certification.
        self.assertTrue(71<float(june['altitude_deg'])<72)
        self.assertTrue(24<float(winter['altitude_deg'])<26)
        self.assertTrue(180<float(june['azimuth_deg'])<190)

    def test_hash_leap_calendar_and_missing_solar_field_reject_before_output(self):
        base=json.loads(BASIS.read_text(encoding='utf-8'))
        for mode in ('hash','leap','missing'):
            row=copy.deepcopy(base);weather=WEATHER
            if mode=='hash':row['weather']['sha256']='wrong'
            if mode=='leap':row['calendar_year']=2024
            if mode=='missing':
                records=gzip.decompress(WEATHER.read_bytes()).decode('utf-8').splitlines();fields=records[8].split(',');fields[13]='9999';records[8]=','.join(fields)
                raw=('\n'.join(records)+'\n').encode();weather=self.root/'missing.epw';weather.write_bytes(raw);row['weather']['sha256']=hashlib.sha256(raw).hexdigest()
            path=self.root/(mode+'.json');path.write_text(json.dumps(row),encoding='utf-8');out=self.root/('reject-'+mode)
            with self.subTest(mode=mode),self.assertRaises(ProjectError):run(weather,path,out,PYTHON)
            self.assertFalse(out.exists())
