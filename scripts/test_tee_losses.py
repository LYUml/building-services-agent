import json
import math
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from probe_tee_assembly import run as assemble
from probe_tee_losses import run

ROOT=Path(__file__).resolve().parents[1]

class TeeLossTests(unittest.TestCase):
    def test_saved_binding_signed_reference_and_controls(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);spec=ROOT/'examples/tee-trial/spec.json';assembly=ROOT/'examples/tee-trial/assembly.json'
            assemble(spec,assembly,root/'model');model=root/'model/assembly.ifc'
            data=json.loads((ROOT/'examples/tee-trial/loss-basis.json').read_text(encoding='utf-8-sig'))
            basis=root/'basis.json';basis.write_text(json.dumps(data))
            a=run(model,spec,assembly,basis,root/'first')
            # Independent equal-bore 90-degree, branch fraction 1/4 reference.
            self.assertAlmostEqual(a['paths']['run']['k_combined_velocity'],-.0625)
            self.assertAlmostEqual(a['paths']['branch']['k_combined_velocity'],1.0378515625)
            dynamic=998/2*(.001/(math.pi*.032**2/4))**2
            self.assertAlmostEqual(a['paths']['run']['signed_k_times_dynamic_pressure_pa'],-.0625*dynamic)
            self.assertNotEqual(a['inlet_guid'],a['paths']['run']['outlet_guid'])
            data['inlet_port']='main-b';data['run_flow_m3_s']*=2;data['branch_flow_m3_s']*=2
            basis.write_text(json.dumps(data));b=run(model,spec,assembly,basis,root/'reverse')
            self.assertEqual(a['inlet_guid'],b['paths']['run']['outlet_guid'])
            self.assertAlmostEqual(b['reference_dynamic_pressure_pa'],4*a['reference_dynamic_pressure_pa'])
            data['inlet_port']='branch';basis.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'main-leg'):run(model,spec,assembly,basis,root/'invalid')
            self.assertFalse((root/'invalid').exists())
            data['inlet_port']='main-a';basis.write_text(json.dumps(data))
            f=ifcopenshell.open(str(model));f.by_type('IfcPipeSegment')[0].Representation.Representations[0].Items[0].Depth+=.01
            changed=root/'changed.ifc';f.write(str(changed))
            with self.assertRaisesRegex(ValueError,'geometry/identity'):run(changed,spec,assembly,basis,root/'tampered')

if __name__=='__main__':unittest.main()
