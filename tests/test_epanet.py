import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.epanet import validate,run,evaluate
from bsa.epanet_energy import darcy_factor,pipe_loss
import math

ROOT=Path(__file__).resolve().parents[1]


def case():
    return json.loads((ROOT/'examples/water-loop/project.json').read_text())


class WaterInputTests(unittest.TestCase):
    def test_rejects_unsupported_assumptions_and_unbounded_inputs(self):
        for change in (lambda p:p.update(pressure_basis='total pressure Pa'),
                       lambda p:p['fluid'].update(specific_gravity=.8),
                       lambda p:p['fluid'].update(relative_viscosity=.001),
                       lambda p:p['solver'].update(max_runtime_s=True),
                       lambda p:p['solver'].update(velocity_tolerance_m_s=0),
                       lambda p:p['pipes'][0].update(length_m=1),
                       lambda p:p['pipes'][0].update(source='unknown'),
                       lambda p:p['pumps'][0].update(head_curve=[[0,60],[.004,45],[.008,20]]),
                       lambda p:p['junctions'].append(dict(p['junctions'][0],id='DISCONNECTED'))):
            p=case();change(p)
            with self.assertRaises(ProjectError):validate(p)

    def test_zero_flow_and_friction_regime_boundaries(self):
        result=pipe_loss(case()['pipes'][0],0,1)
        self.assertEqual(result['regime'],'stagnant');self.assertIsNone(result['darcy_factor'])
        self.assertEqual(result['model_head_loss_m'],0)
        self.assertEqual(darcy_factor(1000,.001),(.064,'laminar'))
        for boundary in (2000,4000):
            left=darcy_factor(boundary-1e-5,.001)[0]
            right=darcy_factor(boundary+1e-5,.001)[0]
            self.assertAlmostEqual(left,right,places=8)


@unittest.skipUnless(importlib.util.find_spec('wntr'),'requires optional water runtime')
class WaterEngineTests(unittest.TestCase):
    def execute(self,p):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        source=Path(folder.name)/'project.json';source.write_text(json.dumps(p))
        original=digest(source);out=Path(folder.name)/'run'
        result=run(source,out)
        self.assertEqual(original,digest(source));self.assertTrue(result['input_unchanged'])
        return result,out

    def test_real_loop_symmetry_reverse_flow_and_native_artifacts(self):
        p=case();r,out=self.execute(p)
        self.assertTrue(r['calculated_checks_pass'],r)
        self.assertFalse(r['design_accepted']);self.assertEqual(r['independent_cycle_count'],1)
        pipes={v['id']:v for v in r['pipes']};nodes={v['id']:v for v in r['junctions']}
        # Symmetric network and equal A/B withdrawals imply identical branch flows.
        self.assertAlmostEqual(pipes['JA']['flow_m3_s'],.002,delta=1e-7)
        self.assertAlmostEqual(pipes['JB']['flow_m3_s'],.002,delta=1e-7)
        self.assertAlmostEqual(pipes['AC']['flow_m3_s'],.001,delta=1e-7)
        self.assertAlmostEqual(pipes['CB']['flow_m3_s'],-.001,delta=1e-7)
        self.assertAlmostEqual(nodes['A']['head_m'],nodes['B']['head_m'],places=5)
        self.assertEqual(r['runtime']['engine_version'],20200)
        self.assertFalse(r['runtime']['energy_analysis_performed'])
        self.assertIsNone(r['pumps'][0]['electrical_power_kw'])
        for name in ('network.inp','network.rpt','network.bin','raw.json','link-flowrate.csv','node-pressure.csv'):
            self.assertTrue((out/name).is_file(),name)
            self.assertEqual(digest(out/name),r['artifacts'][name])
        with self.assertRaises(ProjectError):run(out/'source-copy.json',out)
        with self.assertRaises(FileExistsError):run(out.parent/'project.json',out)
        # Independent audit must detect corrupted solver outputs.
        raw=json.loads((out/'raw.json').read_text());raw['links']['flowrate']['JA']+=.001
        failed=evaluate(p,raw)
        self.assertFalse(failed['checks']['mass_balance']);self.assertFalse(failed['calculated_checks_pass'])

    def test_pressure_driven_shortfall_is_retained_as_failed_design(self):
        p=case();p['pumps'][0]['head_curve']=[[0,20],[.002,15],[.004,10],[.008,2]]
        r,_=self.execute(p)
        self.assertNotIn('engine_error',r,r)
        self.assertTrue(r['checks']['engine_clean'])
        self.assertTrue(r['checks']['demand_law'])
        self.assertFalse(r['checks']['pressure_targets']);self.assertFalse(r['checks']['delivery_targets'])
        self.assertFalse(r['calculated_checks_pass'])
        terminal=next(j for j in r['junctions'] if j['id']=='C')
        self.assertGreater(terminal['delivered_fraction'],0)
        self.assertLess(terminal['delivered_fraction'],.99)

    def test_demand_driven_parallel_pipes_split_known_withdrawal(self):
        p=case();p['hydraulics']['demand_model']='DDA';p['pumps']=[]
        p['reservoirs'][0]['head_m']=50
        p['junctions']=[dict(p['junctions'][-1],id='END',elevation_m=0)]
        pipe=dict(p['pipes'][0],length_m=10,**{'from':'R','to':'END'})
        p['pipes']=[dict(pipe,id='ONE'),dict(pipe,id='TWO')]
        r,_=self.execute(p)
        self.assertTrue(r['calculated_checks_pass'],r)
        for pipe in r['pipes']:self.assertAlmostEqual(pipe['flow_m3_s'],.001,delta=1e-8)

    def test_velocity_crosscheck_does_not_relax_physical_limit(self):
        p=case()
        for pipe in p['pipes']:pipe['maximum_velocity_m_s']=.5
        r,_=self.execute(p)
        self.assertTrue(all(v['native_velocity_match'] for v in r['pipes']))
        self.assertFalse(r['checks']['velocity_limits']);self.assertFalse(r['calculated_checks_pass'])

    def test_circulation_error_passes_mass_balance_but_fails_energy(self):
        p=case();r,out=self.execute(p);raw=json.loads((out/'raw.json').read_text())
        # Add circulation around the ring, preserving every nodal mass balance.
        # Also update velocity so Q/A consistency cannot detect the corruption.
        for pipe in p['pipes']:
            id=pipe['id'];raw['links']['flowrate'][id]+=-.0001 if id=='JB' else .0001
            raw['links']['velocity'][id]=abs(raw['links']['flowrate'][id])/(math.pi*pipe['diameter_m']**2/4)
        failed=evaluate(p,raw)
        for key in ('mass_balance','head_pressure_identity','demand_law','velocity_limits','pump_curves'):
            self.assertTrue(failed['checks'][key],key)
        self.assertFalse(failed['checks']['pipe_energy']);self.assertFalse(failed['calculated_checks_pass'])
        # Uniform head/pressure shift preserves pipe drops but violates reservoir boundary.
        raw=json.loads((out/'raw.json').read_text())
        for field in ('head','pressure'):
            for id in raw['nodes'][field]:raw['nodes'][field][id]+=1
        failed=evaluate(p,raw)
        self.assertTrue(failed['checks']['pipe_energy']);self.assertTrue(failed['checks']['head_pressure_identity'])
        self.assertFalse(failed['checks']['reservoir_heads'])

    def single_pipe(self,demand,viscosity=1):
        p=case();p['hydraulics']['demand_model']='DDA';p['pumps']=[]
        p['fluid']['relative_viscosity']=viscosity;p['reservoirs'][0]['head_m']=50
        p['junctions']=[dict(p['junctions'][-1],id='END',elevation_m=0,demand_m3_s=demand)]
        p['pipes']=[dict(p['pipes'][0],id='LINE',length_m=10,diameter_m=.04,minor_k=0,**{'from':'R','to':'END'})]
        return p

    def test_native_laminar_loss_matches_independent_poiseuille_calculation(self):
        p=self.single_pipe(1e-5,1000);pipe=p['pipes'][0]
        r,_=self.execute(p);self.assertTrue(r['calculated_checks_pass'],r)
        e=r['pipes'][0]['energy'];self.assertEqual(e['regime'],'laminar')
        # Independent SI Poiseuille solution, with explicitly documented engine
        # gravity/viscosity and its legacy cubic-foot flow convention.
        expected=128*10*(1000*1.1e-5*.3048**2)*(1e-5*.3048**3/.028317)/(math.pi*(32.2*.3048)*.04**4)
        self.assertAlmostEqual(e['observed_head_drop_m'],expected,delta=1e-5)
        # The linear laminar resistance predicts doubling flow doubles friction head.
        self.assertAlmostEqual(pipe_loss(pipe,2e-5,1000)['friction_head_m'],2*e['model_head_loss_m'],delta=1e-7)

    def test_native_transition_loss_and_reversed_orientation(self):
        # Choose native Re=3000, rather than relying on ambiguous approximate SI conversion.
        q=3000*math.pi*(.04/.3048)*1.1e-5/4*.028317
        p=self.single_pipe(q);p['pipes'][0].update(minor_k=3)
        r,_=self.execute(p);self.assertTrue(r['calculated_checks_pass'],r)
        energy=r['pipes'][0]['energy'];self.assertEqual(energy['regime'],'transition')
        self.assertAlmostEqual(energy['reynolds'],3000,delta=.001)
        p['pipes'][0].update(**{'from':'END','to':'R'})
        reversed_result,_=self.execute(p)
        self.assertTrue(reversed_result['calculated_checks_pass'],reversed_result)
        self.assertLess(reversed_result['pipes'][0]['energy']['model_head_loss_m'],0)
        self.assertAlmostEqual(reversed_result['pipes'][0]['energy']['model_head_loss_m'],-energy['model_head_loss_m'],places=6)

    def test_native_zero_withdrawal_dead_end_has_no_singular_energy_check(self):
        p=self.single_pipe(.001)
        p['junctions'].append(dict(p['junctions'][0],id='DEAD',demand_m3_s=0))
        p['pipes'].append(dict(p['pipes'][0],id='DEADLEG',**{'from':'END','to':'DEAD'}))
        r,_=self.execute(p)
        self.assertTrue(r['calculated_checks_pass'],r)
        dead=next(pipe for pipe in r['pipes'] if pipe['id']=='DEADLEG')
        self.assertAlmostEqual(dead['flow_m3_s'],0,delta=1e-10)
        self.assertTrue(dead['energy']['energy_pass'])

    def test_workflow_runs_and_integrity_detects_native_input_tamper(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as f:
            out=Path(f)/'workflow';r=execute(ROOT/'examples/water-loop/plan.json',out)
            self.assertTrue(r['execution_pass'],r);self.assertFalse(r['design_accepted'])
            self.assertTrue(verify(out)['integrity_pass'])
            (out/'water/network.inp').write_text('changed')
            self.assertFalse(verify(out)['integrity_pass'])
