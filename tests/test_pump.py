import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from bsa.engine import ProjectError
from bsa.pump import MODEL,validate_curve,prepare,interpolate,solve,run

ROOT=Path(__file__).resolve().parents[1]


def case(root_flow=2e-6):
    # Independent Poiseuille resistance: delta_p = 128 mu L Q / (pi D^4).
    resistance=128*1*2/(math.pi*.01**4);slope=1e9
    intercept=100+(resistance+slope)*root_flow
    network=dict(name='Synthetic viscous laminar line',model='steady incompressible circular tree',sources={'test':'Synthetic independent analytic fixture; no product or regulation data'},
        fluid=dict(density_kg_m3=1000,dynamic_viscosity_pa_s=1,source='test'),supply=dict(node='IN',total_pressure_pa=100000,source='test'),
        nodes=[dict(id='IN',elevation_m=0,demand_m3_s=0,required_total_pressure_pa=0,source='test'),dict(id='OUT',elevation_m=0,demand_m3_s=1.5e-6,required_total_pressure_pa=100,source='test')],
        segments=[dict(id='PIPE',diameter_m=.01,length_m=2,roughness_m=0,minor_k=0,max_velocity_m_s=1,source='test',**{'from':'IN','to':'OUT'})])
    curve=dict(model=MODEL,sources={'test':'Synthetic descending total-pressure and combined wire-to-water efficiency fixture'},source='test',speed_rpm=1000,
        fluid=dict(density_kg_m3=1000,dynamic_viscosity_pa_s=1),inlet_total_pressure_pa=0,efficiency_basis='wire to water',
        points=[dict(flow_m3_s=q,total_pressure_rise_pa=intercept-slope*q,wire_to_water_efficiency=.5) for q in (1e-6,3e-6)],
        flow_bracket_m3_s=[1e-6,3e-6],flow_tolerance_m3_s=1e-13,pressure_tolerance_pa=.001,max_iterations=100)
    return network,curve,resistance


class PumpInputTests(unittest.TestCase):
    def test_curve_contract_and_no_extrapolation(self):
        _,curve,_=case()
        for mutate in (lambda c:c.update(speed_rpm=True),lambda c:c.update(max_iterations=0),
                       lambda c:c['points'].reverse(),lambda c:c['points'][0].update(wire_to_water_efficiency=1.1),
                       lambda c:c.update(efficiency_basis='pump shaft only'),lambda c:c.update(source='unknown')):
            data=copy.deepcopy(curve);mutate(data)
            with self.assertRaises(ProjectError):validate_curve(data)
        with self.assertRaises(ProjectError):interpolate(curve,0)
        with self.assertRaises(ProjectError):interpolate(curve,4e-6)

    def test_fluid_branches_and_transition_are_not_silently_approximated(self):
        network,curve,_=case();bad=copy.deepcopy(curve);bad['fluid']['density_kg_m3']=998
        with self.assertRaises(ProjectError):prepare(network,bad)
        branch=copy.deepcopy(network);branch['nodes'].append(dict(branch['nodes'][-1],id='OTHER'))
        branch['segments'].append(dict(branch['segments'][0],id='BRANCH',**{'to':'OTHER'}))
        with self.assertRaises(ProjectError):prepare(branch,curve)
        network['fluid']['dynamic_viscosity_pa_s']=curve['fluid']['dynamic_viscosity_pa_s']=.0001
        with self.assertRaisesRegex(ProjectError,'transitional'):prepare(network,curve)


@unittest.skipUnless(importlib.util.find_spec('fluids'),'requires network runtime')
class PumpOperatingTests(unittest.TestCase):
    def test_intersection_matches_independent_laminar_solution_and_power_units(self):
        network,curve,resistance=case();before=copy.deepcopy(network)
        result,selected=solve(network,curve);point=result['operating_point']
        self.assertTrue(result['calculated_checks_pass']);self.assertEqual(network,before)
        self.assertAlmostEqual(point['flow_m3_s'],2e-6,delta=1e-13)
        self.assertAlmostEqual(point['pump_total_pressure_rise_pa'],100+resistance*2e-6,delta=.001)
        self.assertAlmostEqual(point['hydraulic_power_kw'],point['flow_m3_s']*point['pump_total_pressure_rise_pa']/1000)
        self.assertAlmostEqual(point['estimated_electrical_kw'],point['hydraulic_power_kw']/.5)
        self.assertLessEqual(abs(point['residual_pa']),curve['pressure_tolerance_pa'])
        self.assertEqual(next(n for n in selected['nodes'] if n['id']=='OUT')['source'],'pump/operating_point')
        self.assertFalse(result['design_accepted'])

    def test_shutoff_point_is_retained_but_solver_uses_explicit_positive_bracket(self):
        network,curve,_=case()
        curve['points'].insert(0,dict(flow_m3_s=0,total_pressure_rise_pa=20000,wire_to_water_efficiency=0))
        result,_=solve(network,curve)
        self.assertTrue(result['calculated_checks_pass'])
        self.assertTrue(all(row['flow_m3_s']>0 for row in result['trace']))
        self.assertEqual(curve['points'][0]['flow_m3_s'],0)
        curve['flow_bracket_m3_s']=[0,3e-6]
        with self.assertRaises(ProjectError):prepare(network,curve)

    def test_nonzero_inlet_pressure_is_not_counted_as_pump_added_power(self):
        network,curve,resistance=case();curve['inlet_total_pressure_pa']=5000
        intercept=curve['points'][0]['total_pressure_rise_pa']+1e9*1e-6
        expected=(intercept+5000-100)/(resistance+1e9)
        result,_=solve(network,curve);point=result['operating_point']
        self.assertTrue(result['calculated_checks_pass'])
        self.assertAlmostEqual(point['flow_m3_s'],expected,delta=1e-13)
        self.assertAlmostEqual(point['supply_total_pressure_pa']-point['pump_total_pressure_rise_pa'],5000)
        self.assertAlmostEqual(point['hydraulic_power_kw'],point['flow_m3_s']*point['pump_total_pressure_rise_pa']/1000)

    def test_insufficient_capacity_velocity_and_missing_efficiency_remain_explicit(self):
        network,curve,_=case(1.2e-6);result,_=solve(network,curve)
        self.assertEqual(result['status'],'converged');self.assertFalse(result['checks']['minimum_design_flow'])
        self.assertFalse(result['calculated_checks_pass']);self.assertIsNotNone(result['operating_point'])
        network,curve,_=case();network['segments'][0]['max_velocity_m_s']=.01
        result,_=solve(network,curve);self.assertFalse(result['checks']['velocity_through_bracket'])
        curve['efficiency_basis']='not supplied'
        for point in curve['points']:point.pop('wire_to_water_efficiency')
        network['segments'][0]['max_velocity_m_s']=1
        result,_=solve(network,curve);self.assertIsNone(result['operating_point']['estimated_electrical_kw'])
        self.assertTrue(result['calculated_checks_pass'])

    def test_missing_bracket_and_iteration_exhaustion_preserve_failure_evidence(self):
        network,curve,_=case()
        for point,pressure in zip(curve['points'],[100,50]):point['total_pressure_rise_pa']=pressure
        result,selected=solve(network,curve)
        self.assertEqual(result['status'],'not_bracketed');self.assertIsNone(selected);self.assertEqual(len(result['trace']),2)
        network,curve,_=case(2.17e-6);curve['max_iterations']=1
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'network.json';c=root/'curve.json'
            p.write_text(json.dumps(network));c.write_text(json.dumps(curve))
            result=run(p,c,root/'run');self.assertEqual(result['status'],'not_converged')
            self.assertTrue((root/'run/iterations.csv').is_file());self.assertTrue((root/'run/pump.json').is_file())
            self.assertFalse((root/'run/operating-network.json').exists());self.assertTrue(result['inputs_unchanged'])

    def test_direct_workflow_and_failed_producer_do_not_fabricate_pump_state(self):
        from bsa.workflow import execute,verify
        from bsa.cli import digest
        network,curve,_=case()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'network.json').write_text(json.dumps(network));(root/'curve.json').write_text(json.dumps(curve))
            brief=root/'brief.md';brief.write_text('Calculate the sourced pump operating state and retain failures.\n')
            tasks=[dict(id='pump',kind='pump_operating_point',project='network.json',curve='curve.json')]
            def plan():
                return dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=tasks,
                    requirements=[dict(id='R'+str(i),passage='P001',quote='Calculate the sourced pump operating state and retain failures.',task=t['id'],acceptance='Source bracket, rerun and retained failures') for i,t in enumerate(tasks)])
            path=root/'plan.json';path.write_text(json.dumps(plan()));result=execute(path,root/'direct')
            self.assertTrue(result['execution_pass']);self.assertTrue(verify(root/'direct')['integrity_pass'])
            network['supply']['total_pressure_pa']=0;(root/'network.json').write_text(json.dumps(network))
            catalogue=dict(sources={'test':'Synthetic single candidate'},options=[dict(id='ONLY',diameter_m=.01,roughness_m=0,material_score_per_m=1,source='test')],allowed_options={'PIPE':['ONLY']},objective='minimise sum(length_m * material_score_per_m)',max_evaluations=1,
                hydraulic_basis=dict(assumption='prescribed demands; route and local K unchanged across sizes',source='test'))
            (root/'catalogue.json').write_text(json.dumps(catalogue))
            tasks[:]=[dict(id='design',kind='network_design',project='network.json',catalogue='catalogue.json'),dict(id='pump',kind='pump_operating_point',depends_on='design',curve='curve.json')]
            path.write_text(json.dumps(plan()));result=execute(path,root/'failed')
            self.assertEqual(result['tasks']['design']['status'],'fail');self.assertEqual(result['tasks']['pump']['status'],'pending')
            self.assertFalse((root/'failed/pump').exists())

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('manifold3d'),'requires model/clash runtimes')
    def test_model_derived_workflow_and_pump_artifact_integrity(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run';result=execute(ROOT/'examples/water-riser/pump-plan.json',out)
            self.assertTrue(result['execution_pass']);self.assertTrue(verify(out)['integrity_pass'])
            pump=json.loads((out/'pump/pump.json').read_text())
            self.assertAlmostEqual(pump['operating_point']['flow_m3_s'],.0012534852,delta=1e-10)
            self.assertGreater(pump['operating_point']['estimated_electrical_kw'],pump['operating_point']['hydraulic_power_kw'])
            original=json.loads((out/'electrical/calculations.json').read_text())
            self.assertEqual(original['circuits'][0]['connected_electrical_kw'],.75)
            path=out/'pump/operating-network.json';path.write_bytes(path.read_bytes()+b'\n')
            self.assertFalse(verify(out)['integrity_pass'])


if __name__=='__main__':unittest.main()
