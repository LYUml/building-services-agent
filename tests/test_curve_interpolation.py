import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from bsa.curve_interpolation import segment_bound,curve_bound
from bsa.engine import ProjectError
from bsa.cli import digest
ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'runs/tcf-fan-intake-v1/tcf-m300.pdf';EXTRACTION=ROOT/'runs/tcf-calibrated-vectors-v2'
PYTHON=ROOT/'tools/pdf2plot-runtime/Scripts/python.exe'

class CurveInterpolationTests(unittest.TestCase):
    def test_reciprocal_has_distinct_absolute_and_relative_maxima(self):
        r=segment_bound(1,100,2,50)
        self.assertAlmostEqual(r['relative_maximum_flow'],1.5)
        self.assertAlmostEqual(r['maximum_relative_pressure_excess'],.125)
        self.assertAlmostEqual(r['absolute_maximum_flow'],math.sqrt(2))
        self.assertAlmostEqual(r['maximum_absolute_pressure_excess_pa'],100*(1.5-math.sqrt(2)))

    def test_analytic_bounds_cover_independent_dense_sampling(self):
        for exponent in (-.1,-1,-3,-10):
            x0,y0,x1=2.,300.,3.;y1=y0*(x1/x0)**exponent
            r=segment_bound(x0,y0,x1,y1)
            for i in range(1001):
                x=x0+(x1-x0)*i/1000
                original=y0*(x/x0)**exponent
                chord=y0+(y1-y0)*(x-x0)/(x1-x0)
                self.assertLessEqual(chord/original-1,r['maximum_relative_pressure_excess']+1e-12)
                self.assertLessEqual(chord-original,r['maximum_absolute_pressure_excess_pa']+1e-10)

    def test_invalid_domains_reject_and_curve_keeps_all_segments(self):
        for values in ((0,100,1,50),(1,100,1,50),(1,50,2,100),(1,100,2,float('nan'))):
            with self.assertRaises(ProjectError):segment_bound(*values)
        r=curve_bound([(1,100),(2,50),(3,25)])
        self.assertEqual(r['segment_count'],2)
        self.assertEqual(r['maximum_relative_pressure_excess'],max(s['maximum_relative_pressure_excess'] for s in r['segments']))

@unittest.skipUnless(PDF.is_file() and PYTHON.is_file() and (EXTRACTION/'extraction.json').is_file(),'requires actual pinned source extraction/runtime')
class ActualInterpolationAuditTests(unittest.TestCase):
    def test_native_source_audit_and_rehashed_point_tampering(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);out=root/'audit'
            command=[str(PYTHON),str(ROOT/'scripts/check_tcf_interpolation.py'),'--pdf',str(PDF),'--extraction',str(EXTRACTION),'--out',str(out)]
            r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            data=json.loads((out/'interpolation.json').read_text())
            self.assertTrue(data['native_source_points_match']);self.assertEqual(len(data['curves']),6)
            self.assertTrue(all(c['segment_count']==200 for c in data['curves']));self.assertFalse(data['solver_ready'])
            copy=root/'copy';shutil.copytree(EXTRACTION,copy)
            raw=copy/'disjoint-paths.json';p=json.loads(raw.read_text());p['paths'][0]['points'][0]['x']+=.01;raw.write_text(json.dumps(p))
            report=copy/'extraction.json';p=json.loads(report.read_text());p['artifacts']['disjoint-paths.json']=digest(raw);report.write_text(json.dumps(p))
            command[command.index('--extraction')+1]=str(copy);command[-1]=str(root/'blocked')
            r=subprocess.run(command,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('native PDF',r.stderr);self.assertFalse((root/'blocked').exists())
