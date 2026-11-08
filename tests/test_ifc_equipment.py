import copy
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.ifc_equipment import validate_settings,extract
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'examples/hvac-drawing/settings.json'


class EquipmentSettingsTests(unittest.TestCase):
    def test_missing_duplicate_and_invalid_callouts(self):
        p=json.loads(SETTINGS.read_text());validate_settings(p)
        for value in (0,float('nan'),True):
            q=copy.deepcopy(p);q['annotation_height_m']=value
            with self.assertRaises(ProjectError):validate_settings(q)
        q=copy.deepcopy(p);q['tags'][1]['tag']=q['tags'][0]['tag'].lower()
        with self.assertRaises(ProjectError):validate_settings(q)


@unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus source report')
class EquipmentDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name);cls.out=cls.root/'workflow'
        from bsa.native_cad import DEFAULT_EXE
        cls.result=execute(ROOT/'examples/hvac-drawing-plan.json',cls.out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']),autocad=DEFAULT_EXE if os.environ.get('BSA_TEST_AUTOCAD') else None)
        if cls.result['tasks']['drawing']['status']!='pass':raise AssertionError(cls.result['tasks']['drawing'])
        cls.ifc=cls.out/'thermal/analysis.ifc';cls.report=cls.out/'thermal/thermal-binding.json';cls.settings=json.loads(SETTINGS.read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_complete_schedule_geometry_identity_and_units(self):
        import ezdxf
        self.assertTrue(verify(self.out)['integrity_pass'])
        with (self.out/'drawing/equipment.csv').open(newline='') as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),3);self.assertEqual({r['guid'] for r in rows},{r['guid'] for r in self.settings['tags']})
        office=next(r for r in rows if r['zone']=='Office')
        self.assertEqual(float(office['cooling_capacity_thermal_kw']),4)
        self.assertEqual(float(office['heating_capacity_thermal_kw']),5)
        self.assertEqual(float(office['supply_flow_l_s']),200)
        doc=ezdxf.readfile(self.out/'drawing/equipment.dxf');self.assertEqual(doc.header['$INSUNITS'],6)
        refs=list(doc.modelspace().query('LINE[layer=="BSA_EQUIPMENT_REFERENCE"]'))
        self.assertEqual(len(refs),3)
        for ref in refs:self.assertAlmostEqual(ref.dxf.start.distance(ref.dxf.end),.9)
        texts=[e.dxf.text for e in doc.modelspace().query('TEXT')]
        for row in rows:
            self.assertIn(row['guid'],texts);self.assertIn(row['tag'],texts)

    def test_producer_artifact_changes_and_failed_results_rejected(self):
        original=self.out/'thermal/annual/baseline/summary.json';raw=original.read_bytes()
        try:
            original.write_bytes(raw+b' ')
            with self.assertRaisesRegex(ProjectError,'artifact missing/changed'):extract(self.ifc,self.report,self.settings)
        finally:original.write_bytes(raw)
        q=copy.deepcopy(self.settings);q['tags'].pop()
        with self.assertRaisesRegex(ProjectError,'cover every'):extract(self.ifc,self.report,q)
        failed=self.out/'thermal/failed-report.json';data=json.loads(self.report.read_text());data['calculated_checks_pass']=False;failed.write_text(json.dumps(data))
        try:
            with self.assertRaisesRegex(ProjectError,'passing saved'):extract(self.ifc,failed,self.settings)
        finally:failed.unlink()

    @unittest.skipUnless(os.environ.get('BSA_TEST_AUTOCAD'),'requires isolated AutoCAD 2027')
    def test_actual_native_dwg_reopen_scale_and_clipped_sheet_guard(self):
        from bsa.ifc_native import run
        r=json.loads((self.out/'native/native-verification.json').read_text())
        self.assertTrue(r['native_reopen_pass']);self.assertTrue(r['plot']['pdf_reference_pass'])
        self.assertEqual(r['plot']['reference_expected_mm'],9)
        self.assertTrue((self.out/'native/equipment.dwg').is_file())
        p=json.loads((ROOT/'examples/hvac-drawing/sheet.json').read_text());p['window_drawing_units']=[-1,-6,17,10]
        path=self.root/'clipped.json';path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'annotation extents'):run(self.out/'drawing/equipment.dxf',path,self.root/'clipped')
        self.assertFalse((self.root/'clipped').exists())
