import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.regulations import evaluate
from bsa.water_pipe_regulations import run

ROOT=Path(__file__).resolve().parents[1]


class WaterPipeRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
        self.bases=json.loads((ROOT/'examples/regulations-hk-water/bases.json').read_text())
        self.project=copy.deepcopy(next(iter(self.bases.values())))
        self.pdf=self.root/'emsd-bec-2024.pdf';self.pdf.write_bytes(b'SYNTHETIC TEST SOURCE ONLY')
        self.pack['sources']['emsd_bec_2024']['sha256']=digest(self.pdf)
        self.set('velocity',1.2,'m/s');self.set('linear_friction',400,'Pa/m')

    def set(self,key,value,unit=None):
        self.project['water_pipe'][key]=dict(value=value,source='Synthetic unit-test input',**({'unit':unit} if unit else {}))
    def status(self):return evaluate(self.pack,self.project,self.root)['checks'][0]['status']

    def test_small_diameter_boundary_and_velocity(self):
        self.set('code_diameter',50,'mm');self.set('linear_friction',999,'Pa/m')
        self.assertEqual(self.status(),'pass')
        self.set('velocity',1.20001,'m/s');self.assertEqual(self.status(),'review_required')
        self.set('code_diameter',50.001,'mm');self.assertEqual(self.status(),'review_required')
        self.set('linear_friction',400,'Pa/m');self.assertEqual(self.status(),'pass')

    def test_large_fixed_and_variable_limits_and_controls(self):
        self.set('code_diameter',80,'mm');self.set('velocity',2.5,'m/s')
        self.assertEqual(self.status(),'pass')
        self.set('velocity',2.50001,'m/s');self.assertEqual(self.status(),'review_required')
        self.set('flow_mode','variable');self.assertEqual(self.status(),'pending')
        for control in self.pack['rules'][0]['allowed_variable_pump_controls']:
            self.set('pump_control',control);self.set('velocity',3,'m/s');self.assertEqual(self.status(),'pass')
            self.set('velocity',3.00001,'m/s');self.assertEqual(self.status(),'review_required')
        self.set('velocity',3,'m/s');self.set('pump_control','single_fixed_speed_throttle')
        self.assertEqual(self.status(),'review_required')
        self.set('pump_control','variable_speed');self.set('linear_friction',400.001,'Pa/m')
        self.assertEqual(self.status(),'review_required')

    def test_missing_units_source_scope_and_nonphysical(self):
        for value in (True,-1,float('nan')):
            self.set('velocity',value,'m/s');self.assertEqual(self.status(),'pending')
        self.set('velocity',1.2,'km/h');self.assertEqual(self.status(),'pending')
        self.set('velocity',1.2,'m/s');self.pdf.write_bytes(b'changed')
        self.assertEqual(self.status(),'pending')

    def test_fresh_hydraulics_binding_and_pressure_failure(self):
        network=json.loads((ROOT/'examples/regulations-hk-water/network.json').read_text())
        pp=self.root/'pack.json';pp.write_text(json.dumps(self.pack))
        bp=self.root/'bases.json';bp.write_text(json.dumps(self.bases))
        np=self.root/'network.json';np.write_text(json.dumps(network))
        r=run(np,bp,pp,self.root,self.root/'pass')
        self.assertEqual(r['status'],'pass');self.assertFalse(r['design_accepted'])
        calculated=json.loads((self.root/'pass/network/network.json').read_text())
        bound=json.loads((self.root/'pass/bound-pipe-projects.json').read_text())
        for seg in calculated['segments']:
            source=next(s for s in network['segments'] if s['id']==seg['id'])
            self.assertAlmostEqual(bound[seg['id']]['water_pipe']['linear_friction']['value'],seg['friction_pa']/source['length_m'])
        network['supply']['total_pressure_pa']=0;np.write_text(json.dumps(network))
        r=run(np,bp,pp,self.root,self.root/'low-pressure')
        self.assertTrue(r['supported_checks_pass']);self.assertEqual(r['status'],'fail')
        next(iter(self.bases.values()))['water_pipe']['velocity']={'value':0}
        bp.write_text(json.dumps(self.bases))
        with self.assertRaisesRegex(ProjectError,'cannot be overridden'):run(np,bp,pp,self.root,self.root/'override')


if __name__=='__main__':unittest.main()
