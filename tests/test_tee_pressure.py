import json
from pathlib import Path
import tempfile
import unittest
from bsa.tee_pressure import run,CONTRACT
from bsa.tee_assembly import run as assemble
from bsa.network import GRAVITY
ROOT=Path(__file__).resolve().parents[1]

class TeePressureTests(unittest.TestCase):
    def test_failed_pressure_blocks_downstream(self):
        import shutil
        from bsa.workflow import execute
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for path in (ROOT/'examples/tee-trial').glob('*'):
                if path.is_file():shutil.copyfile(path,root/path.name)
            plan=json.loads((root/'pressure-plan.json').read_text())
            plan['tasks'].append(dict(id='diagnostic',kind='tee_losses',depends_on='assembly',basis='loss-basis.json',requires_pass=['pressure']))
            requirement=dict(plan['requirements'][-1]);requirement.update(id='diagnostic',task='diagnostic');plan['requirements'].append(requirement)
            (root/'plan.json').write_text(json.dumps(plan))
            path=root/'pressure-basis.json';data=json.loads(path.read_text());data['inlet_total_pressure_pa']=0;path.write_text(json.dumps(data))
            report=execute(root/'plan.json',root/'blocked')
            self.assertEqual(report['tasks']['pressure']['status'],'fail')
            self.assertEqual(report['tasks']['diagnostic']['status'],'pending')
            self.assertFalse((root/'blocked/diagnostic').exists())

    def test_pressure_failures_signed_energy_and_laminar_reference(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);source=ROOT/'examples/tee-trial';spec=source/'spec.json';assembly=source/'assembly.json'
            assemble(spec,assembly,root/'model');model=root/'model/assembly.ifc'
            data=json.loads((source/'pressure-basis.json').read_text());basis=root/'basis.json'
            # Low-flow laminar case permits an independent Hagen-Poiseuille reference.
            data.update(run_flow_m3_s=3e-6,branch_flow_m3_s=1e-6)
            basis.write_text(json.dumps(data));a=run(model,spec,assembly,basis,root/'positive')
            self.assertTrue(a['calculated_checks_pass'])
            import math
            friction=128*.001*.2*(4e-6+3e-6)/(math.pi*.032**4)
            self.assertAlmostEqual(a['paths']['run']['pipe_friction_pa'],friction)
            self.assertAlmostEqual(a['paths']['run']['elevation_pa'],998*GRAVITY*.6)
            dynamic=998/2*(4e-6/(math.pi*.032**2/4))**2
            self.assertAlmostEqual(a['paths']['run']['outlet_total_pressure_pa'],100000-friction+.05*dynamic-998*GRAVITY*.6)
            data['inlet_total_pressure_pa']=90000;basis.write_text(json.dumps(data))
            b=run(model,spec,assembly,basis,root/'low');self.assertFalse(b['checks']['pressure_targets'])
            self.assertFalse(b['calculated_checks_pass'])
            data.update(k_run=-10,k_branch=0);basis.write_text(json.dumps(data))
            c=run(model,spec,assembly,basis,root/'energy');self.assertFalse(c['checks']['nonnegative_net_fitting_dissipation'])
            data['coefficient_contract']='unspecified Crane coefficient';basis.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'face-to-face'):run(model,spec,assembly,basis,root/'invalid')
            self.assertFalse((root/'invalid').exists())

if __name__=='__main__':unittest.main()
