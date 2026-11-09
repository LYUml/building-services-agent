import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
MOD=runpy.run_path(str(ROOT/'scripts/extract_tcf_vectors.py'))
PDF=ROOT/'runs/tcf-fan-intake-v1/tcf-m300.pdf'
PYTHON=ROOT/'tools/pdf2plot-runtime/Scripts/python.exe'
HELPER=ROOT/'tools/pdf2plot-99a8ee1/pdf2plot_helper.py'

class NativeCurveContinuityTests(unittest.TestCase):
    def test_disconnected_lines_keep_all_starts(self):
        chains=MOD['split_lines']([('l',(0,0),(1,1)),('l',(1,1),(2,2)),('l',(10,10),(11,11))])
        self.assertEqual(chains,[[(0.,0.),(1.,1.),(2.,2.)],[(10.,10.),(11.,11.)]])
    def test_unknown_primitive_and_nonfinite_reject(self):
        for items in [[('c',(0,0),(1,1),(2,2),(3,3))],[('l',(0,0),(float('nan'),1))]]:
            with self.assertRaises(ValueError):MOD['split_lines'](items)

@unittest.skipUnless(PDF.is_file() and PYTHON.is_file() and HELPER.is_file(),'requires pinned isolated pdf2plot runtime and manufacturer PDF')
class ActualVectorExtractionTests(unittest.TestCase):
    def test_actual_disjoint_curves_calibration_and_pin_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);out=root/'result'
            command=[str(PYTHON),str(ROOT/'scripts/extract_tcf_vectors.py'),'--pdf',str(PDF),'--helper',str(HELPER),'--out',str(out)]
            r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            data=json.loads((out/'extraction.json').read_text())
            self.assertEqual(data['curve_count'],6);self.assertEqual(data['points_per_curve'],201);self.assertEqual(data['discontinuities_preserved'],5)
            self.assertLessEqual(data['independent_log_export_relative_error'],5e-6);self.assertFalse(data['solver_ready'])
            fake=root/'helper.py';fake.write_text('raise RuntimeError("must not run")')
            command[command.index('--helper')+1]=str(fake);command[-1]=str(root/'blocked')
            r=subprocess.run(command,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('pinned',r.stderr)
            self.assertFalse((root/'blocked').exists())
