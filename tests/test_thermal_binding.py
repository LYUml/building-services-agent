import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.bim import run as author
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.thermal_binding import extract,validate_contract
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/thermal-ifc'


class ThermalBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        cls.folder=Path(cls.temp.name)
        author(EXAMPLE/'bim.json',cls.folder/'bim')
        cls.ifc=cls.folder/'bim/model.ifc'
        cls.binding=json.loads((EXAMPLE/'binding.json').read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_actual_geometry_and_millimetre_units(self):
        import ifcopenshell
        from ifcopenshell.util.unit import convert_file_length_units
        before=digest(self.ifc)
        rows,audit=extract(self.ifc,self.binding)
        self.assertEqual([r['size_m'] for r in rows],[[8,6,3],[5,6,3],[4,6,3]])
        self.assertEqual(sum(r['floor_area_m2'] for r in audit['spaces']),102)
        mm=self.folder/'millimetres.ifc'
        convert_file_length_units(ifcopenshell.open(str(self.ifc)),'MILLIMETERS').write(str(mm))
        scaled,meta=extract(mm,self.binding)
        self.assertAlmostEqual(meta['length_unit_scale_to_m'],.001)
        self.assertEqual([(r['origin_m'],r['size_m']) for r in scaled],[(r['origin_m'],r['size_m']) for r in rows])
        self.assertEqual(digest(self.ifc),before)

    def test_mapping_coverage_and_duplicate_geometry_rejected(self):
        b=copy.deepcopy(self.binding);b['spaces'].pop()
        with self.assertRaisesRegex(ProjectError,'every saved'):extract(self.ifc,b)
        p=json.loads((EXAMPLE/'project.json').read_text())
        validate_contract(p,self.binding)
        p['building']['spaces']=[]
        with self.assertRaisesRegex(ProjectError,'omit geometry'):validate_contract(p,self.binding)
        b=copy.deepcopy(self.binding);b['spaces'][1]['guid']=b['spaces'][0]['guid']
        with self.assertRaisesRegex(ProjectError,'duplicate'):validate_contract(json.loads((EXAMPLE/'project.json').read_text()),b)
        b=copy.deepcopy(self.binding);b['north_axis_deg']=float('nan')
        with self.assertRaisesRegex(ProjectError,'north axis'):validate_contract(json.loads((EXAMPLE/'project.json').read_text()),b)

    def test_missing_engine_keeps_task_pending(self):
        result=execute(ROOT/'examples/thermal-ifc-plan.json',self.folder/'pending')
        self.assertEqual(result['tasks']['thermal']['status'],'pending')
        self.assertFalse((self.folder/'pending/thermal/annual').exists())

    def test_solid_not_just_bounds_and_saved_placement(self):
        import ifcopenshell
        import ifcopenshell.api as api
        import numpy as np
        model=ifcopenshell.open(str(self.ifc))
        obj=model.by_guid(self.binding['spaces'][0]['guid'])
        item=obj.Representation.Representations[0].Items[0]
        points=item.Coordinates.CoordList
        points=[list(p) for p in points];points[0][0]=.5
        item.Coordinates.CoordList=points
        bad=self.folder/'not-box.ifc';model.write(str(bad))
        with self.assertRaises(ProjectError):extract(bad,self.binding)
        model=ifcopenshell.open(str(self.ifc));obj=model.by_guid(self.binding['spaces'][0]['guid'])
        matrix=np.eye(4);matrix[:3,3]=[25,2,4]
        api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)
        placed=self.folder/'placed.ifc';model.write(str(placed))
        rows,_=extract(placed,self.binding)
        self.assertEqual(rows[0]['origin_m'],[25,2,4])
        matrix[:2,:2]=[[.8,-.6],[.6,.8]]
        api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)
        model.write(str(placed))
        with self.assertRaisesRegex(ProjectError,'axis-aligned'):extract(placed,self.binding)

    @unittest.skipUnless(os.environ.get('BSA_TEST_ENERGYPLUS'),'requires actual EnergyPlus')
    def test_saved_bim_to_annual_workflow(self):
        out=self.folder/'workflow'
        result=execute(ROOT/'examples/thermal-ifc-plan.json',out,energyplus=Path(os.environ['BSA_TEST_ENERGYPLUS']))
        self.assertTrue(verify(out)['integrity_pass'])
        audit=json.loads((out/'thermal/thermal-binding.json').read_text())
        self.assertTrue(audit['calculated_checks_pass'])
        self.assertEqual(digest(out/'model/model.ifc'),digest(out/'thermal/model.ifc'))
        annual=json.loads((out/'thermal/annual/annual.json').read_text())
        import openstudio as sdk
        saved=sdk.model.Model.load(sdk.path(str(out/'thermal/annual/baseline/model.osm'))).get()
        self.assertEqual(saved.getBuilding().northAxis(),30)
        self.assertEqual(annual['results']['baseline']['metadata']['floor_area_m2'],102)
        self.assertAlmostEqual(annual['results']['baseline']['summary']['analytic_lighting_kwh'],10722.24)
        self.assertFalse(annual['design_accepted'])
