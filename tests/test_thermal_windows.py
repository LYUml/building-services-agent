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
from bsa.energy import build
from bsa.thermal_windows import validate,audit,extract,VARIABLES
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/thermal-windows/project.json'


def fixture():
    p=json.loads(PROJECT.read_text())['building'];p.pop('hvac')
    p.update(spaces=[dict(id='Room',source='Synthetic elevated translated box',origin_m=[10,-5,2],size_m=[6,5,3])],site=dict(latitude_deg=0,longitude_deg=0,timezone_h=0,elevation_m=0),design_days=[])
    for row,face in zip(p['windows'],('X-','X+','Y-','Y+')):row.update(zone='Room',face=face,offset_m=.8,sill_m=1,width_m=1.5,height_m=1.2)
    return p


class WindowInputTests(unittest.TestCase):
    def test_sources_physics_fit_overlap_and_internal_faces(self):
        p=fixture();rows=p['windows'];validate(rows,p['spaces'])
        for key,value in [('source',''),('width_m',0),('face','NORTH'),('zone','Missing'),('width_m',100),('sill_m',True)]:
            q=copy.deepcopy(rows);q[0][key]=value
            with self.subTest(key=key),self.assertRaises(ProjectError):validate(q,p['spaces'])
        for key,value in [('u_factor_w_m2k',0),('shgc',1),('visible_transmittance',0),('source',''),('shgc',float('nan'))]:
            q=copy.deepcopy(rows);q[0]['glazing'][key]=value
            with self.subTest(key=key),self.assertRaises(ProjectError):validate(q,p['spaces'])
        q=copy.deepcopy(rows);q[1].update(face='X-',offset_m=.9)
        with self.assertRaisesRegex(ProjectError,'overlapping'):validate(q,p['spaces'])
        spaces=[dict(id='Room',origin_m=[0,0,0],size_m=[6,5,3]),dict(id='Neighbor',origin_m=[6,0,0],size_m=[6,5,3])]
        with self.assertRaisesRegex(ProjectError,'interzone'):validate(rows,spaces)

    def test_saved_four_faces_translated_vertices_and_net_opaque_area(self):
        p=fixture()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            r=build(p,12,Path(folder));a=r['window_audit']
            self.assertTrue(a['saved_windows_match']);self.assertAlmostEqual(a['window_area_m2'],7.2)
            self.assertAlmostEqual(r['material_audit']['role_area_m2']['exterior_wall'],66)
            self.assertAlmostEqual(r['material_audit']['role_net_opaque_area_m2']['exterior_wall'],58.8)
            for row in a['windows']:
                self.assertAlmostEqual(min(v[2] for v in row['vertices_m']),3)
                self.assertAlmostEqual(row['area_m2'],1.8)
            coords={row['face']:[p[0 if row['face'][0]=='X' else 1] for p in row['vertices_m']] for row in a['windows']}
            self.assertTrue(all(v==10 for v in coords['X-']));self.assertTrue(all(v==16 for v in coords['X+']))
            self.assertTrue(all(v==-5 for v in coords['Y-']));self.assertTrue(all(v==0 for v in coords['Y+']))

    def test_saved_glazing_geometry_type_multiplier_and_source_tampering(self):
        import openstudio as sdk
        p=fixture()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            build(p,12,Path(folder));path=sdk.path(str(Path(folder)/'model.osm'))
            for mode in ('glazing','geometry','type','multiplier','source','frame'):
                model=sdk.model.Model.load(path).get();window=model.getSubSurfaces()[0]
                if mode=='glazing':model.getSimpleGlazings()[0].setUFactor(3.1)
                elif mode=='geometry':
                    points=sdk.Point3dVector()
                    for point in window.vertices():points.append(sdk.Point3d(point.x(),point.y(),point.z()+.01))
                    window.setVertices(points)
                elif mode=='type':window.setSubSurfaceType('OperableWindow')
                elif mode=='multiplier':window.setMultiplier(2)
                elif mode=='frame':window.setWindowPropertyFrameAndDivider(sdk.model.WindowPropertyFrameAndDivider(model))
                else:window.additionalProperties().setFeature('Source','Wrong source')
                with self.subTest(mode=mode),self.assertRaises(ProjectError):audit(model,p['windows'],p['spaces'])


@unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
class WindowEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name);cls.out=cls.root/'workflow'
        r=execute(ROOT/'examples/thermal-windows-plan.json',cls.out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']))
        if r['tasks']['thermal']['status']!='pass':raise AssertionError(r['tasks']['thermal'])
        cls.annual=json.loads((cls.out/'thermal/annual/annual.json').read_text());cls.p=cls.annual['source_data'];cls.base=cls.annual['results']['baseline']

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_actual_calendar_solar_geometry_and_monthly_annual_results(self):
        self.assertTrue(verify(self.out)['integrity_pass'])
        self.assertAlmostEqual(self.base['metadata']['window_audit']['window_area_m2'],6.48)
        self.assertAlmostEqual(self.base['metadata']['material_audit']['role_net_opaque_area_m2']['exterior_wall'],131.52)
        r=self.base['summary']['windows'];self.assertTrue(r['calculated_checks_pass'])
        self.assertEqual(len(r['annual']),16);self.assertEqual(len(r['monthly']),192)
        solar=[r for r in r['annual'] if r['quantity']=='transmitted solar']
        self.assertEqual(len(solar),4);self.assertTrue(all(r['kwh']>0 and r['hours']==8760 for r in solar))
        self.assertFalse(self.annual['design_accepted'])

    def test_native_units_coverage_and_solar_bound_failures(self):
        for mode in ('units','missing','solar'):
            path=self.root/(mode+' # window.sql');shutil.copyfile(self.out/'thermal/annual/baseline/eplusout.sql',path)
            with closing(sqlite3.connect(path)) as con:
                if mode=='units':con.execute("UPDATE ReportDataDictionary SET Units='kWh' WHERE Name='Surface Window Heat Gain Energy'")
                elif mode=='missing':con.execute("DELETE FROM ReportData WHERE ReportDataIndex=(SELECT MIN(ReportDataIndex) FROM ReportData WHERE ReportDataDictionaryIndex IN (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary WHERE Name='Surface Window Heat Gain Energy'))")
                else:con.execute("UPDATE ReportData SET Value=Value+1e12 WHERE ReportDataDictionaryIndex IN (SELECT ReportDataDictionaryIndex FROM ReportDataDictionary WHERE Name='Surface Window Transmitted Solar Radiation Energy' AND KeyValue='WIN W01')")
                con.commit()
            if mode=='solar':
                r,_=extract(path,self.base['metadata']['window_audit'],2025,self.p['solver']);self.assertFalse(r['checks']['transmitted_solar_incident_bound']);self.assertFalse(r['calculated_checks_pass'])
            else:
                with self.assertRaises(ProjectError):extract(path,self.base['metadata']['window_audit'],2025,self.p['solver'])

    def test_lower_declared_shgc_changes_actual_transmitted_solar(self):
        from bsa.annual_energy import run
        p=copy.deepcopy(self.p)
        for row in p['building']['windows']:row['glazing']['shgc']=.2
        project=self.root/'lower-shgc.json';project.write_text(json.dumps(p),encoding='utf-8')
        r=run(project,self.out/'thermal/annual/weather.epw',self.root/'lower-shgc',Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertTrue(r['calculated_checks_pass'])
        before={r['window']:r['kwh'] for r in self.base['summary']['windows']['annual'] if r['quantity']=='transmitted solar'}
        after={r['window']:r['kwh'] for r in r['results']['baseline']['summary']['windows']['annual'] if r['quantity']=='transmitted solar'}
        self.assertTrue(all(0<after[k]<before[k] for k in before))
