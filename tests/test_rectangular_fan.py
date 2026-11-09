import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from fluids.friction import Colebrook
from bsa.rectangular_fan import solve,run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'

class RectangularFanTests(unittest.TestCase):
    def setUp(self):
        self.project=json.loads((EX/'fan-project.json').read_text())
        self.curve=json.loads((EX/'fan-curve.json').read_text())

    def test_balance_against_independent_scalar_pressure(self):
        r,selected=solve(self.project,self.curve)
        q=r['operating_point']['flow_m3_s'];area=.5*.3;dh=2*area/(.5+.3)
        velocity=q/area;re=1.2*velocity*dh/1.8e-5
        system=30+(Colebrook(re,9e-5/dh)*10/dh+1)*1.2*velocity**2/2
        fan=100-(q-.3)*90/.6
        self.assertAlmostEqual(fan,system,delta=1e-5)
        self.assertAlmostEqual(q,.6526898147,delta=1e-8)
        self.assertTrue(r['calculated_checks_pass'])
        self.assertEqual(selected['nodes'][-1]['demand_m3_s'],q)
        self.assertNotIn('estimated_electrical_kw',r['operating_point'])
        self.assertAlmostEqual(r['operating_point']['air_power_kw'],q*fan/1000)
        self.assertFalse(r['design_accepted'])

    def test_unbracketed_does_not_extrapolate(self):
        self.curve['points'][0]['total_pressure_rise_pa']=20
        self.curve['points'][1]['total_pressure_rise_pa']=10
        r,selected=solve(self.project,self.curve)
        self.assertEqual(r['status'],'not_bracketed');self.assertIsNone(selected)
        self.assertFalse(r['calculated_checks_pass'])

    def test_insufficient_design_flow_and_velocity_fail_separately(self):
        self.project['nodes'][-1]['demand_m3_s']=.8
        r,_=solve(self.project,self.curve)
        self.assertFalse(r['checks']['minimum_design_flow']);self.assertFalse(r['calculated_checks_pass'])
        self.project['nodes'][-1]['demand_m3_s']=.5
        self.project['segments'][0]['max_velocity_m_s']=3
        r,_=solve(self.project,self.curve)
        self.assertFalse(r['checks']['velocity_through_bracket']);self.assertFalse(r['calculated_checks_pass'])

    def test_static_efficiency_density_and_unstable_curves_reject(self):
        variants=[]
        for key,value in [('pressure_basis','fan static pressure'),('efficiency_basis','wire to water')]:
            c=copy.deepcopy(self.curve);c[key]=value;variants.append(c)
        c=copy.deepcopy(self.curve);c['fluid']['density_kg_m3']=1.3;variants.append(c)
        c=copy.deepcopy(self.curve);c['points'][1]['total_pressure_rise_pa']=110;variants.append(c)
        c=copy.deepcopy(self.curve);c['flow_bracket_m3_s']=[.2,.9];variants.append(c)
        for c in variants:
            with self.subTest(c=c),self.assertRaises(ProjectError):solve(self.project,c)

    def test_branches_and_transitional_domain_reject(self):
        p=json.loads((EX/'project.json').read_text())
        with self.assertRaises(ProjectError):solve(p,self.curve)
        self.curve['points'][0]['flow_m3_s']=.0001
        self.curve['flow_bracket_m3_s'][0]=.0001
        with self.assertRaisesRegex(ProjectError,'turbulent'):solve(self.project,self.curve)

    def test_iteration_budget_retains_failure(self):
        self.curve['max_iterations']=1
        r,selected=solve(self.project,self.curve)
        self.assertEqual(r['status'],'not_converged');self.assertFalse(r['calculated_checks_pass']);self.assertIsNone(selected)

    def test_saved_operating_network_rerun(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'result';r=run(EX/'fan-project.json',EX/'fan-curve.json',out)
            self.assertTrue(r['inputs_unchanged']);self.assertTrue(r['selected_rerun_pass'])
            saved=json.loads((out/'analysis/network.json').read_text())
            self.assertEqual(saved['supply_flow_m3_s'],r['operating_point']['flow_m3_s'])
            self.assertEqual(saved['segments'][0]['area_m2'],.15)

    def test_workflow_failure_blocks_review_and_pins_methods(self):
        from bsa.workflow import execute,verify,validate_plan
        import shutil
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder)
            for name in ('fan-project.json','fan-curve.json','fan-plan.json','fan-brief.md'):shutil.copyfile(EX/name,root/name)
            path=root/'fan-plan.json'
            _,inputs=validate_plan(path)
            self.assertIn(ROOT/'src/bsa/pump.py',inputs)
            r=execute(path,root/'positive')
            self.assertEqual(r['tasks']['fan']['status'],'pass')
            self.assertEqual(r['tasks']['review']['status'],'pending')
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            project=root/'fan-project.json';data=json.loads(project.read_text());data['nodes'][-1]['demand_m3_s']=.8;project.write_text(json.dumps(data))
            r=execute(path,root/'failed')
            self.assertEqual(r['tasks']['fan']['status'],'fail')
            self.assertIn('required checks unresolved',r['tasks']['review']['scope'])
            self.assertFalse(verify(root/'positive')['integrity_pass'])

