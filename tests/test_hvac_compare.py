import json
from pathlib import Path
import tempfile
import unittest
from bsa.hvac_compare import run


class HVACCompareTests(unittest.TestCase):
    def make_scenario(self,delta):
        from tests.test_allocation_lookup import AllocationLookupTests
        f=AllocationLookupTests();f.setUp();self.addCleanup(f.temp.cleanup)
        f.allocation['load_inputs']['temperature_difference']['value']=delta
        ducts=dict(basis='Synthetic comparison',air=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009),tree=dict(root='R',sections=[dict(id=k,**{'from':'R','to':t}) for k,t in [('SA','A'),('SB','B')]],leaf_terminals=dict(A=['A'],B=['B']),basis='Synthetic'),sections=[dict(id=k,width_m=.8,height_m=.4,limits=dict(actual_velocity_m_s=8,friction_Pa_m=2,aspect_ratio=4)) for k in ['SA','SB']])
        (f.root/'ducts.json').write_text(json.dumps(ducts),encoding='utf-8')
        f.plan['tasks'].append(dict(id='ducts',kind='duct_schedule',project='ducts.json',depends_on='allocation'))
        f.plan['requirements'].append(dict(f.plan['requirements'][0],id='RD',task='ducts'))
        f.run_plan('workflow');return f.root/'workflow'

    def test_independent_scenarios_and_stale_evidence(self):
        a=self.make_scenario(10);b=self.make_scenario(8)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'comparison.json';r=run(a,b,out)
            self.assertGreater(r['total_supply_change_L_s'],0)
            self.assertIn('temperature_difference',r['load_input_changes'])
            self.assertIsNone(r['selected_scenario']);self.assertFalse(r['design_accepted'])
            with self.assertRaisesRegex(ValueError,'Distinct'):run(a,b,out)
            (b/'ducts/results.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'evidence changed'):run(a,b,Path(tmp)/'stale.json')
