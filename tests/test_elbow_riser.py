import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import ezdxf
from bsa.cli import digest
from bsa.native_cad import DEFAULT_EXE
from bsa.workflow import execute, verify

ROOT=Path(__file__).resolve().parents[1]
AVAILABLE=all(importlib.util.find_spec(p) for p in ('ifcopenshell','manifold3d','fluids'))


@unittest.skipUnless(AVAILABLE,'requires IFC, clash and network runtimes')
class IndependentElbowRiserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'runs').mkdir(exist_ok=True)
        cls.folder=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.folder.name)
        cls.example=ROOT/'examples/elbow-riser'
        cls.before={p:digest(p) for p in cls.example.iterdir() if p.is_file()}
        cls.autocad=DEFAULT_EXE if os.environ.get('BSA_TEST_AUTOCAD')=='1' and DEFAULT_EXE.is_file() else None
        cls.out=cls.root/'good'
        cls.result=execute(cls.example/'plan.json',cls.out,autocad=cls.autocad)

    @classmethod
    def tearDownClass(cls):
        assert all(digest(p)==h for p,h in cls.before.items())
        cls.folder.cleanup()

    def test_independent_gravity_friction_minor_loss_and_complete_geometry(self):
        self.assertEqual(self.result['tasks']['model']['status'],'pass')
        self.assertEqual(self.result['tasks']['qa']['status'],'pass')
        model=json.loads((self.example/'project.json').read_text())
        old=json.loads((ROOT/'examples/circular-elbow/project.json').read_text())
        self.assertNotEqual(model['project_uuid'],old['project_uuid'])
        report=json.loads((self.out/'model/analysis/network.json').read_text())['segments'][0]
        length=3+math.pi*.24/2;velocity=.00006/(math.pi*.06**2/4)
        friction=128*.0012*length*.00006/(math.pi*.06**4)
        minor=.6*997*velocity**2/2;gravity=997*9.80665*2.04
        self.assertAlmostEqual(report['friction_pa'],friction,places=10)
        self.assertAlmostEqual(report['minor_pa'],minor,places=10)
        self.assertAlmostEqual(report['elevation_pressure_pa'],gravity,places=7)
        self.assertAlmostEqual(report['downstream_total_pressure_pa'],25000-friction-minor-gravity,places=7)
        self.assertLess(report['reynolds'],2000)
        self.assertTrue(verify(self.out)['integrity_pass'])
        self.assertFalse(self.result['design_accepted'])

    def test_clockwise_flow_keeps_true_ccw_dxf_geometry_and_proven_leaders(self):
        drawing=json.loads((self.out/'drawing/drawing.json').read_text())
        self.assertEqual(drawing['piece_count'],3)
        bend=next(p for p in drawing['pieces'] if p['name']=='TURN')
        self.assertAlmostEqual(bend['start_world_m'][0],3.76)
        self.assertAlmostEqual(bend['start_world_m'][2],2.5)
        self.assertAlmostEqual(bend['end_world_m'][0],4)
        self.assertAlmostEqual(bend['end_world_m'][2],2.74)
        doc=ezdxf.readfile(self.out/'drawing/segments.dxf')
        arc=doc.modelspace().query('ARC[layer=="BSA_PIPE_AXIS"]')[0]
        self.assertAlmostEqual(arc.dxf.radius,.24)
        self.assertAlmostEqual(arc.dxf.start_angle,90)
        self.assertAlmostEqual(arc.dxf.end_angle,180)
        self.assertTrue(arc.start_point.isclose((4,2.74,0),abs_tol=1e-8))
        self.assertTrue(arc.end_point.isclose((3.76,2.5,0),abs_tol=1e-8))
        self.assertEqual(arc.get_xdata('BSA_IFC')[0].value,bend['guid'])
        for key in ('leader_body_checks_pass','leader_pair_checks_pass','saved_leader_paths_match'):
            self.assertTrue(drawing['annotation_layout'][key])

    def test_inadequate_supply_retains_failure_and_blocks_all_dependents(self):
        inputs=self.root/'bad-inputs';inputs.mkdir()
        for p in self.example.iterdir():
            if p.is_file():shutil.copyfile(p,inputs/p.name)
        path=inputs/'network.json';network=json.loads(path.read_text())
        network['name']='Intentionally inadequate independent riser supply'
        network['supply']['total_pressure_pa']=20000
        path.write_text(json.dumps(network))
        out=self.root/'bad';result=execute(inputs/'plan.json',out,autocad=self.autocad)
        self.assertEqual(result['tasks']['model']['status'],'fail')
        self.assertTrue((out/'model/bim/model.ifc').is_file())
        for task in ('qa','drawing','native'):
            self.assertEqual(result['tasks'][task]['status'],'pending')
            self.assertFalse((out/task).exists())
        pressure=json.loads((out/'model/analysis/network.json').read_text())['segments'][0]['downstream_total_pressure_pa']
        self.assertLess(pressure,2000)
        self.assertTrue(verify(out)['integrity_pass'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_AUTOCAD')=='1' and DEFAULT_EXE.is_file(),'requires local AutoCAD')
    def test_actual_elevation_native_reopen_and_72_mm_reference(self):
        self.assertEqual(self.result['tasks']['native']['status'],'pass')
        report=json.loads((self.out/'native/native-verification.json').read_text())
        self.assertTrue(report['native_reopen_pass'])
        self.assertAlmostEqual(report['plot']['reference_expected_mm'],72)
        self.assertAlmostEqual(report['plot']['reference_measured_mm'],72,delta=.2)
        self.assertEqual(report['plot']['visual_review'],'pending')


if __name__=='__main__':unittest.main()
