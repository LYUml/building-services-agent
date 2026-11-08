import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.electrical_fault import GROUPS,prepare,solve,run

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return (json.loads((ROOT/'examples/office-electrical/project.json').read_text()),
            json.loads((ROOT/'examples/fault-data.json').read_text()))


class FaultVerificationTests(unittest.TestCase):
    def test_independent_complex_loop_and_adiabatic_values(self):
        project,data=inputs();before=copy.deepcopy((project,data));result=solve(project,data);row=result['circuits'][0]
        self.assertEqual(result['status'],'pass');self.assertFalse(result['design_accepted'])
        self.assertAlmostEqual(row['values']['loop_r_ohm_hot'],.8)
        self.assertAlmostEqual(row['values']['loop_x_ohm'],.054)
        self.assertAlmostEqual(row['values']['minimum_earth_fault_a'],218.5/math.hypot(.8,.054))
        self.assertAlmostEqual(row['values']['minimum_earth_fault_a'],272.504905286556,places=9)
        self.assertAlmostEqual(row['values']['cpc_energy_capacity_a2s'],29756.25)
        self.assertAlmostEqual(row['values']['minimum_cpc_section_from_source_bound_mm2'],math.sqrt(20000)/115)
        self.assertEqual((project,data),before)

    def test_resistive_case_and_exact_source_boundaries(self):
        project,data=inputs();project['supply_voltage_v']=240;row=data['circuits'][0]
        row['loop'].update(external_r_ohm_hot=3.4,external_x_ohm_hot=0,loop_x_ohm_per_m=0,minimum_voltage_factor=1)
        row['device'].update(nominal_voltage_min_v=240,nominal_voltage_max_v=240)
        row['limits']['maximum_disconnection_time_s']=.1;row['max_fault']['prospective_max_fault_a']=6000
        row['energy']['maximum_let_through_a2s']=29756.25
        result=solve(project,data)
        self.assertEqual(result['status'],'pass');self.assertEqual(result['circuits'][0]['values']['minimum_earth_fault_a'],60)

    def test_each_missing_group_stays_pending_without_default_data(self):
        for group in GROUPS:
            with self.subTest(group=group):
                project,data=inputs();data['circuits'][0][group]=None;result=solve(project,data)
                self.assertEqual(result['status'],'pending');self.assertFalse(result['calculated_checks_pass'])
                self.assertIn('missing '+group+' source group',result['circuits'][0]['unverified'])

    def test_uncovered_curve_energy_voltage_time_remain_unverified(self):
        for mode in ('trip','energy','voltage','time','adiabatic'):
            with self.subTest(mode=mode):
                project,data=inputs();row=data['circuits'][0]
                if mode=='trip':row['device']['trip_current_min_a']=1000
                elif mode=='energy':row['energy']['fault_current_min_a']=1000
                elif mode=='voltage':row['device'].update(nominal_voltage_min_v=240,nominal_voltage_max_v=240)
                elif mode=='time':row['device']['guaranteed_total_clearing_time_s']=1
                else:row['cpc']['maximum_adiabatic_time_s']=.05
                result=solve(project,data)
                self.assertEqual(result['status'],'pending');self.assertTrue(result['circuits'][0]['unverified'])

    def test_insufficient_breaking_capacity_cpc_and_inconsistent_case_fail(self):
        for mode in ('capacity','cpc','inconsistent'):
            with self.subTest(mode=mode):
                project,data=inputs();row=data['circuits'][0]
                if mode=='capacity':row['device']['standalone_breaking_capacity_a']=3000
                elif mode=='cpc':row['cpc']['section_mm2']=1
                else:row['max_fault']['prospective_max_fault_a']=200
                result=solve(project,data);self.assertEqual(result['status'],'fail')
                self.assertTrue(any(value is False for value in result['circuits'][0]['checks'].values()))

    def test_bad_sources_rating_coverage_and_nonfinite_data_rejected(self):
        mutations=[lambda d:d['circuits'][0]['device'].update(rated_current_a=10),
                   lambda d:d.update(model='TT'),lambda d:d['circuits'][0]['loop'].update(minimum_voltage_factor=1.1),
                   lambda d:d['circuits'][0]['loop'].update(external_r_ohm_hot=True),
                   lambda d:d['circuits'][0]['energy'].update(maximum_let_through_a2s=float('nan')),
                   lambda d:d['circuits'].clear(),lambda d:d['circuits'][0]['limits'].update(source='missing')]
        for mutate in mutations:
            project,data=inputs();mutate(data)
            with self.assertRaises(ProjectError):prepare(project,data)

    def test_source_hashes_and_pending_workflow_cannot_be_cleared_by_review(self):
        from bsa.workflow import execute,verify
        from bsa.delivery import template,assess
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);project,data=inputs();data['circuits'][0]['device']=None
            p=root/'project.json';f=root/'faults.json';p.write_text(json.dumps(project));f.write_text(json.dumps(data))
            result=run(p,f,root/'direct');self.assertEqual(result['status'],'pending');self.assertTrue(result['inputs_unchanged'])
            brief=root/'brief.md';quote='Verify the sourced TN fault data and retain unknown guarantees as pending.';brief.write_text(quote+'\n')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[dict(id='faults',kind='electrical_fault',project='project.json',faults='faults.json')],requirements=[dict(id='R1',passage='P001',quote=quote,task='faults',acceptance=quote)])
            path=root/'plan.json';path.write_text(json.dumps(plan));workflow=execute(path,root/'run')
            self.assertEqual(workflow['tasks']['faults']['status'],'pending');self.assertTrue(verify(root/'run')['integrity_pass'])
            review_path=root/'review.json';review=template(path,root/'run',review_path)
            review['requirements'][0].update(status='pass',reviewer='Test assertion',reviewed_at_utc='2026-11-08T00:00:00Z',notes='Cannot replace missing source device evidence',evidence=[dict(artifact='faults/faults.json',sha256=digest(root/'run/faults/faults.json'))])
            review_path.write_text(json.dumps(review));audit=assess(path,root/'run',review_path)
            self.assertEqual(audit['requirements'][0]['effective_review_status'],'pending')

    def test_versioned_workflow_and_artifact_tampering(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run';result=execute(ROOT/'examples/fault-plan.json',out)
            self.assertTrue(result['execution_pass']);self.assertTrue(verify(out)['integrity_pass'])
            artifact=out/'faults/faults.json';artifact.write_bytes(artifact.read_bytes()+b'\n')
            self.assertFalse(verify(out)['integrity_pass'])


if __name__=='__main__':unittest.main()
