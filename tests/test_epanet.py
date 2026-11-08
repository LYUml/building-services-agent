import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.epanet import validate,run,evaluate

ROOT=Path(__file__).resolve().parents[1]


def case():
    return json.loads((ROOT/'examples/water-loop/project.json').read_text())


class WaterInputTests(unittest.TestCase):
    def test_rejects_unsupported_assumptions_and_unbounded_inputs(self):
        for change in (lambda p:p.update(pressure_basis='total pressure Pa'),
                       lambda p:p['fluid'].update(specific_gravity=.8),
                       lambda p:p['solver'].update(max_runtime_s=True),
                       lambda p:p['solver'].update(velocity_tolerance_m_s=0),
                       lambda p:p['pipes'][0].update(length_m=1),
                       lambda p:p['pipes'][0].update(source='unknown'),
                       lambda p:p['pumps'][0].update(head_curve=[[0,60],[.004,45],[.008,20]]),
                       lambda p:p['junctions'].append(dict(p['junctions'][0],id='DISCONNECTED'))):
            p=case();change(p)
            with self.assertRaises(ProjectError):validate(p)


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

    def test_workflow_runs_and_integrity_detects_native_input_tamper(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as f:
            out=Path(f)/'workflow';r=execute(ROOT/'examples/water-loop/plan.json',out)
            self.assertTrue(r['execution_pass'],r);self.assertFalse(r['design_accepted'])
            self.assertTrue(verify(out)['integrity_pass'])
            (out/'water/network.inp').write_text('changed')
            self.assertFalse(verify(out)['integrity_pass'])
