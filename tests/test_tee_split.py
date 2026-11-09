import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa.tee_assembly import run as assemble
from bsa.tee_split import run
ROOT=Path(__file__).resolve().parents[1]
class SplitTests(unittest.TestCase):
    def test_independent_laminar_split_no_root_and_capacity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);source=ROOT/'examples/tee-trial';sp=source/'split-spec.json';ap=source/'split-assembly.json'
            assemble(sp,ap,root/'model');model=root/'model/assembly.ifc';control=source/'split-control.json'
            b=json.loads((source/'split-basis.json').read_text());basis=root/'basis.json';basis.write_text(json.dumps(b))
            a=run(model,sp,ap,basis,control,root/'positive')
            self.assertTrue(a['calculated_checks_pass']);self.assertAlmostEqual(a['branch_fraction'],1/3,places=7)
            expected=500+128*.001/(math.pi*.032**4)*(.2*4e-6+.2*4e-6*2/3)
            self.assertAlmostEqual(a['required_source_total_pressure_pa'],expected,places=7)
            b['inlet_total_pressure_pa']=499;basis.write_text(json.dumps(b))
            fail=run(model,sp,ap,basis,control,root/'weak')
            self.assertTrue(fail['checks']['pressure_balance']);self.assertFalse(fail['checks']['source_pressure_capacity'])
            self.assertFalse(fail['calculated_checks_pass'])
            b['required_outlet_total_pressure_pa']['branch']=10000;basis.write_text(json.dumps(b))
            fail=run(model,sp,ap,basis,control,root/'no-root')
            self.assertFalse(fail['bracketed']);self.assertFalse(fail['calculated_checks_pass'])
            self.assertNotIn('branch_fraction',fail)
if __name__=='__main__':unittest.main()
