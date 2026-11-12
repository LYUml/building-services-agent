import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from fluids.friction import Colebrook
from bsa.cli import digest
from bsa.circular_fan import solve,run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class CircularFanTests(unittest.TestCase):
    def setUp(self):
        self.project=json.loads((ROOT/'examples/route-search/vertical-air-network.json').read_text())
        for node in self.project['nodes']:node['elevation_m']=0
        self.project['segments'][0].update(length_m=6.4,diameter_m=.2032,minor_k=.8)
        self.project['sources']['demo']+=' Independent scalar engine test: assumed6.4m circular line and aggregate K0.8.'
        self.curve=json.loads((ROOT/'examples/route-search/circular-fan-curve.json').read_text())

    def test_operating_point_matches_independent_scalar_pressure_and_air_power(self):
        before=copy.deepcopy(self.project);result,selected=solve(self.project,self.curve)
        q=result['operating_point']['flow_m3_s'];area=math.pi*.2032**2/4;v=q/area;re=1.25*v*.2032/1.8e-5
        system=1+(Colebrook(re,9e-5/.2032)*6.4/.2032+.8)*1.25*v*v/2;fan=17-125*q
        self.assertAlmostEqual(fan,system,delta=1e-8)
        self.assertAlmostEqual(result['operating_point']['air_power_kw'],q*fan/1000)
        self.assertTrue(result['calculated_checks_pass']);self.assertFalse(result['design_accepted'])
        self.assertNotIn('estimated_electrical_kw',result['operating_point'])
        self.assertNotIn('wire_to_water_efficiency',result['operating_point'])
        self.assertEqual(selected['nodes'][-1]['demand_m3_s'],q);self.assertEqual(self.project,before)

    def test_convergence_does_not_clear_insufficient_required_flow(self):
        self.curve['points'][0]['total_pressure_rise_pa']=8;self.curve['points'][1]['total_pressure_rise_pa']=1
        result,selected=solve(self.project,self.curve)
        self.assertEqual(result['status'],'converged');self.assertIsNotNone(selected)
        self.assertFalse(result['checks']['minimum_design_flow']);self.assertFalse(result['calculated_checks_pass'])
        self.assertEqual(result['design_flow_m3_s'],.08)

    def test_unbracketed_or_exhausted_solver_never_fabricates_operating_network(self):
        curve=copy.deepcopy(self.curve);curve['points'][0]['total_pressure_rise_pa']=1;curve['points'][1]['total_pressure_rise_pa']=.1
        result,selected=solve(self.project,curve);self.assertEqual(result['status'],'not_bracketed');self.assertIsNone(selected)
        curve=copy.deepcopy(self.curve);curve['max_iterations']=1
        result,selected=solve(self.project,curve);self.assertEqual(result['status'],'not_converged');self.assertIsNone(selected)

    def test_static_pressure_fluid_mismatch_low_reynolds_and_nonlevel_reject(self):
        for fault in ('static','fluid','reynolds','elevation'):
            project=copy.deepcopy(self.project);curve=copy.deepcopy(self.curve)
            if fault=='static':curve['pressure_basis']='fan static pressure'
            elif fault=='fluid':curve['fluid']['density_kg_m3']=1.2
            elif fault=='reynolds':curve['points'][0]['flow_m3_s']=.001;curve['flow_bracket_m3_s'][0]=.001
            else:project['nodes'][-1]['elevation_m']=1
            with self.subTest(fault=fault),self.assertRaises(ProjectError):solve(project,curve)

    def test_velocity_constraint_remains_separate_from_flow_convergence(self):
        self.project['segments'][0]['max_velocity_m_s']=1
        result,_=solve(self.project,self.curve)
        self.assertTrue(result['checks']['minimum_design_flow']);self.assertFalse(result['checks']['velocity_through_bracket'])
        self.assertFalse(result['calculated_checks_pass'])

    def test_pressure_flag_without_native_lineage_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);producer=root/'producer';producer.mkdir();project=producer/'network-input.json';project.write_text(json.dumps(self.project))
            (producer/'route-pressure.json').write_text(json.dumps(dict(calculated_checks_pass=True,design_accepted=False,inputs={},method_inputs={},artifacts={'network-input.json':digest(project)})))
            with self.assertRaises(ProjectError):run(producer,ROOT/'examples/route-search/circular-fan-curve.json',root/'result')
            self.assertFalse((root/'result').exists())
