import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from bsa.annual_energy import validate,run,extract
from bsa.energy import build
from bsa.engine import ProjectError
from bsa.thermal_geometry import boxes,adjacency

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/annual-energy/three-spaces.json'


class ThermalGeometryTests(unittest.TestCase):
    def test_invalid_geometry(self):
        p=json.loads(PROJECT.read_text())
        self.assertEqual(len(adjacency(boxes(p['building']))),2)
        for field,value in [('id','west'),('source',''),('origin_m',[1,0,0]),
                            ('origin_m',[3,1,0]),('size_m',[0,4,3]),
                            ('origin_m',[True,0,0])]:
            q=copy.deepcopy(p);q['building']['spaces'][1][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ProjectError):validate(q)

    def test_stacked_saved_geometry(self):
        import openstudio as sdk
        p=json.loads(PROJECT.read_text())['building']
        p['spaces']=p['spaces'][:2]
        p['spaces'][1].update(origin_m=[0,0,3],size_m=[3,4,3])
        p.update(site=dict(latitude_deg=0,longitude_deg=0,timezone_h=0,elevation_m=0),design_days=[])
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            meta=build(p,12,Path(folder))
            model=sdk.model.Model.load(sdk.path(str(Path(folder)/'model.osm'))).get()
            self.assertEqual(meta['floor_area_m2'],24)
            matched=[s for s in model.getSurfaces() if s.outsideBoundaryCondition()=='Surface']
            self.assertEqual({s.surfaceType() for s in matched},{'Floor','RoofCeiling'})
            self.assertEqual(len(matched),2)
            self.assertAlmostEqual(sum(s.grossArea() for s in matched),24)

    @unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires real EnergyPlus')
    def test_actual_three_zone_year_and_key_tamper(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'annual'
            r=run(PROJECT,ROOT/'examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz',out,os.environ['BSA_TEST_ENERGYPLUS'])
            self.assertTrue(r['calculated_checks_pass'])
            for name,lpd in [('baseline',12),('variant',6)]:
                case=r['results'][name];meta=case['metadata']
                self.assertEqual(meta['thermal_zones'],3)
                self.assertEqual(meta['floor_area_m2'],48)
                self.assertEqual(meta['matched_surface_count'],4)
                self.assertEqual(len(case['summary']['zone_unmet']),6)
                self.assertAlmostEqual(case['summary']['analytic_lighting_kwh'],48*lpd*8760/1000)
            sql=out/'baseline/eplusout.sql'
            with closing(sqlite3.connect(sql)) as con:
                con.execute("UPDATE ReportDataDictionary SET KeyValue='WRONG ZONE' WHERE KeyValue='WEST'")
                con.commit()
            p=r['source_data']
            with self.assertRaisesRegex(ProjectError,'keys differ'):
                extract(sql,2025,12,48,p['solver'],p['targets'],r['results']['baseline']['metadata'])
