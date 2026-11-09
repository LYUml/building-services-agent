import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa.tee_assembly import run as assemble
from bsa.tee_split import run
ROOT=Path(__file__).resolve().parents[1]
class SplitTableTests(unittest.TestCase):
    def test_variable_coefficient_root_and_invalid_tables(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);source=ROOT/'examples/tee-trial';sp=source/'split-spec.json';ap=source/'split-assembly.json'
            assemble(sp,ap,root/'model');model=root/'model/assembly.ifc';basis=source/'split-basis.json'
            c=json.loads((source/'split-table-control.json').read_text());control=root/'control.json';control.write_text(json.dumps(c))
            report=run(model,sp,ap,basis,control,root/'positive')
            # Hagen-Poiseuille linear friction with K_branch=2*x, K_run=0.
            q=4e-6;d=.032;a=128*.001*q/(math.pi*d**4);dynamic=998/2*(q/(math.pi*d*d/4))**2
            expected=a*.2/(a*(.2+.4)+2*dynamic)
            self.assertTrue(report['calculated_checks_pass']);self.assertAlmostEqual(report['branch_fraction'],expected,places=7)
            self.assertNotAlmostEqual(report['branch_fraction'],1/3,places=3)
            self.assertEqual(report['coefficient_mode'],'piecewise linear table')
            for trial in report['trials']:
                self.assertAlmostEqual(trial['k_branch'],2*trial['fraction'])
                self.assertEqual(trial['k_run'],0)
            for label in ('extrapolation','duplicate','missing-source','nonfinite'):
                bad=json.loads(json.dumps(c))
                if label=='extrapolation':bad['branch_fraction_bounds'][0]=.05
                elif label=='duplicate':bad['coefficient_table']['rows'][1]['branch_fraction']=.1
                elif label=='missing-source':bad['coefficient_table']['source']=''
                else:bad['coefficient_table']['rows'][0]['k_run']=float('nan')
                control.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):run(model,sp,ap,basis,control,root/label)
                self.assertFalse((root/label).exists())
if __name__=='__main__':unittest.main()
