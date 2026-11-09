import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.fan_interpolation_envelope import curves,run,COVERAGE
from bsa.curve_interpolation import segment_bound
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'
PDF=ROOT/'runs/tcf-fan-intake-v1/tcf-m300.pdf';EXTRACTION=ROOT/'runs/tcf-calibrated-vectors-v2'

class FanInterpolationEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.curve=json.loads((EX/'fan-curve.json').read_text())
        self.basis=dict(source='Explicit numerical test assumption, not vendor tolerance',relative_pressure_excess=.01,coverage=COVERAGE,manufacturer_performance_uncertainty=None)

    def test_scaled_chord_brackets_original_log_segment(self):
        self.basis['relative_pressure_excess']=segment_bound(.3,100,.9,10)['maximum_relative_pressure_excess']
        low,high=curves(self.curve,self.basis)
        k=__import__('math').log(.1)/__import__('math').log(3)
        for i in range(101):
            q=.3+.6*i/100;t=(q-.3)/.6
            original=100*(q/.3)**k
            lo=low['points'][0]['total_pressure_rise_pa']*(1-t)+low['points'][1]['total_pressure_rise_pa']*t
            hi=100*(1-t)+10*t
            self.assertLessEqual(lo,original+1e-12);self.assertGreaterEqual(hi,original-1e-12)

    def test_invalid_bounds_and_manufacturer_claims_reject(self):
        for value in (-.1,True,float('inf')):
            b=copy.deepcopy(self.basis);b['relative_pressure_excess']=value
            with self.assertRaises(ProjectError):curves(self.curve,b)
        b=copy.deepcopy(self.basis);b['manufacturer_performance_uncertainty']=.1
        with self.assertRaises(ProjectError):curves(self.curve,b)

    def test_numerical_pass_stays_pending_and_never_design_pass(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);basis=root/'basis.json';basis.write_text(json.dumps(self.basis))
            r=run(EX/'fan-project.json',EX/'fan-curve.json',basis,root/'result')
            self.assertTrue(r['interpolation_only_checks_pass']);self.assertEqual(r['status'],'pending')
            self.assertFalse(r['calculated_checks_pass']);self.assertFalse(r['solver_ready']);self.assertFalse(r['design_accepted'])
            self.assertLess(r['operating_flow_envelope_m3_s'][0],r['operating_flow_envelope_m3_s'][1])

    def test_unbracketed_keeps_failure_without_operating_network(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);basis=root/'basis.json';basis.write_text(json.dumps(self.basis))
            self.curve['points'][0]['total_pressure_rise_pa']=20;curve=root/'curve.json';curve.write_text(json.dumps(self.curve))
            r=run(EX/'fan-project.json',curve,basis,root/'result')
            self.assertEqual(r['status'],'fail');self.assertIsNone(r['operating_flow_envelope_m3_s'])
            self.assertFalse((root/'result/lower/operating-network.json').exists())

@unittest.skipUnless(PDF.is_file() and (EXTRACTION/'extraction.json').is_file() and (ROOT/'tools/pdf2plot-runtime/Scripts/python.exe').is_file(),'requires actual source/runtime')
class RealGraphResearchTests(unittest.TestCase):
    def test_actual_source_native_path_and_no_extrapolation(self):
        runner=runpy.run_path(str(ROOT/'scripts/run_tcf_curve_research.py'))['run']
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            r=runner(PDF,EXTRACTION,Path(folder)/'research')
            inside=r['cases']['within-domain'];outside=r['cases']['outside-domain']
            self.assertTrue(inside['native_path_correspondence_pass']);self.assertEqual(inside['status'],'pending')
            self.assertAlmostEqual(inside['operating_flow_envelope_m3_s'][0],.5375120832,delta=1e-9)
            self.assertEqual(outside['status'],'fail');self.assertTrue(all(s=='not_bracketed' for s in outside['endpoint_status'].values()))
            self.assertFalse(r['design_accepted'])
