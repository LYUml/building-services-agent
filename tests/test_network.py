import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa.network import calculate,validate,friction_factor,run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
AIR=ROOT/'examples/network/air.json'
WATER=ROOT/'examples/network/water.json'


class NetworkTests(unittest.TestCase):
    def test_invalid_topology_and_inputs_rejected(self):
        base=json.loads(AIR.read_text())
        for change in (lambda p:p['segments'][0].update(diameter_m=0),
                       lambda p:p['segments'][0].update(roughness_m=-1),
                       lambda p:p['fluid'].update(dynamic_viscosity_pa_s=0),
                       lambda p:p['nodes'][2].update(demand_m3_s=-0.2),
                       lambda p:p['segments'][1].update(to='MISSING'),
                       lambda p:p['segments'][1].update(to='FAN'),
                       lambda p:p['segments'][1].update(source='unknown'),
                       lambda p:p['segments'][2].update(to='A')):
            p=copy.deepcopy(base);change(p)
            with self.assertRaises(ProjectError):validate(p)

    def test_transitional_flow_requires_explicit_other_model(self):
        with self.assertRaises(ProjectError):friction_factor(3000,0.001)

    def test_laminar_pressure_matches_poiseuille(self):
        p=json.loads(WATER.read_text())
        p['fluid'].update(density_kg_m3=1000,dynamic_viscosity_pa_s=1)
        p['nodes'][1].update(elevation_m=0,demand_m3_s=1e-6,required_total_pressure_pa=0)
        p['segments'][0].update(diameter_m=0.01,length_m=1,roughness_m=0,minor_k=0)
        result=calculate(p);segment=result['segments'][0]
        independent=128*1*1*1e-6/(math.pi*0.01**4)
        self.assertAlmostEqual(segment['friction_pa'],independent,places=8)
        self.assertEqual(segment['regime'],'laminar 64/Re')

    @unittest.skipUnless(importlib.util.find_spec('fluids'),'optional fluids dependency')
    def test_turbulent_factor_satisfies_implicit_colebrook(self):
        f,regime=friction_factor(100000,0.0001)
        residual=1/math.sqrt(f)+2*math.log10(0.0001/3.7+2.51/(100000*math.sqrt(f)))
        self.assertAlmostEqual(residual,0,places=10)

    @unittest.skipUnless(importlib.util.find_spec('fluids'),'optional fluids dependency')
    def test_branch_balance_pressure_and_failure_visibility(self):
        p=json.loads(AIR.read_text());r=calculate(p)
        byid={s['id']:s for s in r['segments']}
        self.assertAlmostEqual(byid['MAIN']['flow_m3_s'],0.5)
        self.assertAlmostEqual(byid['BR-A']['flow_m3_s'],0.2)
        self.assertAlmostEqual(byid['BR-B']['flow_m3_s'],0.3)
        self.assertEqual(r['critical_path'],['MAIN','BR-B'])
        self.assertTrue(r['calculated_checks_pass'])
        p['supply']['total_pressure_pa']=1;p['segments'][0]['max_velocity_m_s']=0.1
        r=calculate(p)
        self.assertFalse(r['calculated_checks']['pressure'])
        self.assertFalse(r['calculated_checks']['velocity'])
        self.assertFalse(r['design_accepted'])

    @unittest.skipUnless(importlib.util.find_spec('fluids'),'optional fluids dependency')
    def test_water_static_pressure_and_saved_manifest(self):
        p=json.loads(WATER.read_text());r=calculate(p);s=r['segments'][0]
        self.assertAlmostEqual(s['elevation_pressure_pa'],998*9.80665*5)
        self.assertAlmostEqual(r['required_source_total_pressure_pa'],100000+s['dissipative_loss_pa']+998*9.80665*5)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run';run(WATER,out)
            self.assertTrue(json.loads((out/'manifest.json').read_text())['input_unchanged'])
            self.assertTrue((out/'segments.csv').is_file())
            with self.assertRaises(FileExistsError):run(WATER,out)

    @unittest.skipUnless(importlib.util.find_spec('fluids'),'optional fluids dependency')
    def test_failed_pressure_budget_marks_workflow_failed(self):
        from bsa.workflow import execute
        from bsa.cli import digest
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);brief=root/'brief.md';brief.write_text('Check this pressure budget.\n')
            p=json.loads(WATER.read_text());p['supply']['total_pressure_pa']=1
            (root/'project.json').write_text(json.dumps(p))
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='network',kind='network',project='project.json')],
                requirements=[dict(id='R1',passage='P001',quote='Check this pressure budget.',task='network',acceptance='minimum node total pressure')])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            result=execute(path,root/'run')
            self.assertEqual(result['tasks']['network']['status'],'fail')
            self.assertFalse(result['execution_pass'])
            self.assertTrue((root/'run/network/network.json').is_file())


if __name__=='__main__':unittest.main()
