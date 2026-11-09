import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from bsa.engine import ProjectError
from bsa.rectangular_network import calculate
from bsa.workflow import execute,verify
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/rectangular-air/project.json'


class RectangularNetworkTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(PROJECT.read_text())

    def test_actual_area_hydraulic_diameter_and_independent_colebrook_residual(self):
        result=calculate(self.p);s=result['segments'][0]
        self.assertAlmostEqual(s['area_m2'],.15)
        self.assertAlmostEqual(s['hydraulic_diameter_m'],.375)
        self.assertAlmostEqual(s['velocity_m_s'],.5/.15)
        self.assertNotAlmostEqual(s['area_m2'],math.pi*.375**2/4)
        f=s['darcy_friction_factor'];re=s['reynolds'];rough=self.p['segments'][0]['roughness_m']/.375
        self.assertAlmostEqual(1/math.sqrt(f)+2*math.log10(rough/3.7+2.51/(re*math.sqrt(f))),0,places=10)
        independent=f*self.p['segments'][0]['length_m']/.375*1.2*(.5/.15)**2/2
        self.assertAlmostEqual(s['friction_pa'],independent,places=10)
        self.assertTrue(result['calculated_checks_pass']);self.assertFalse(result['geometry_bound'])

    def test_branch_continuity_and_pressure_paths(self):
        r=calculate(self.p);s={x['id']:x for x in r['segments']};n={x['id']:x for x in r['nodes']}
        self.assertAlmostEqual(s['MAIN']['flow_m3_s'],s['BR-A']['flow_m3_s']+s['BR-B']['flow_m3_s'])
        loss=s['MAIN']['dissipative_loss_pa']+s['BR-B']['dissipative_loss_pa']
        self.assertAlmostEqual(n['B']['total_pressure_pa'],self.p['supply']['total_pressure_pa']-loss)
        self.assertFalse(r['design_accepted'])

    def test_dimension_rotation_preserves_pressure_and_does_not_mutate_input(self):
        before=copy.deepcopy(self.p);a=calculate(self.p)
        for row in self.p['segments']:row['width_m'],row['height_m']=row['height_m'],row['width_m']
        b=calculate(self.p)
        self.assertEqual(a['required_source_total_pressure_pa'],b['required_source_total_pressure_pa'])
        self.assertNotIn('diameter_m',before['segments'][0])
        self.assertNotIn('diameter_m',self.p['segments'][0])

    def test_unsupported_conditions_and_invalid_dimensions_rejected(self):
        changes=[lambda p:p['method_basis'].update(fully_developed=False),
            lambda p:p['method_basis'].update(source='unknown'),
            lambda p:p['nodes'][1].update(elevation_m=1),
            lambda p:p['segments'][0].update(width_m=0),
            lambda p:p['segments'][0].update(height_m=True),
            lambda p:p['segments'][0].update(diameter_m=.3),
            lambda p:p['segments'][1].update(to='FAN')]
        for change in changes:
            with self.subTest(change=change):
                p=copy.deepcopy(self.p);change(p)
                with self.assertRaises(ProjectError):calculate(p)

    def test_laminar_and_transition_cannot_use_circular_law(self):
        for flow in (1e-6,.001):
            p=copy.deepcopy(self.p)
            for node in p['nodes']:node['demand_m3_s']*=flow
            with self.assertRaisesRegex(ProjectError,'turbulent'):calculate(p)

    def test_failed_velocity_and_source_pressure_retained(self):
        self.p['supply']['total_pressure_pa']=1
        self.p['segments'][0]['max_velocity_m_s']=.1
        r=calculate(self.p)
        self.assertFalse(r['calculated_checks']['velocity']);self.assertFalse(r['calculated_checks']['pressure'])

    def test_workflow_inventory_and_review_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'run';execute(PROJECT.parent/'plan.json',out)
            result=diagnose(PROJECT.parent/'plan.json',out)
            self.assertEqual([r['status'] for r in result['tasks']],['pass','pending'])
            self.assertTrue(verify(out)['integrity_pass'])
            inputs=json.loads((out/'workflow.json').read_text())['inputs']
            self.assertIn(str(ROOT/'src/bsa/rectangular_network.py'),inputs)
            self.assertIn(str(ROOT/'src/bsa/network.py'),inputs)

    def test_failed_budget_blocks_required_consumer(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);self.p['supply']['total_pressure_pa']=1
            (root/'project.json').write_text(json.dumps(self.p),encoding='utf-8')
            for name in ('plan.json','brief.md'):(root/name).write_bytes((PROJECT.parent/name).read_bytes())
            execute(root/'plan.json',root/'run')
            rows={r['id']:r for r in diagnose(root/'plan.json',root/'run')['tasks']}
            self.assertEqual(rows['air']['status'],'fail')
            self.assertEqual(rows['review']['blocked_by'],['air'])
