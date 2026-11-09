import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.fan_mechanical_limits import evaluate,speed_table
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'runs/tcf-fan-intake-v1/tcf-m300.pdf'

@unittest.skipUnless(PDF.is_file(),'requires pinned official TCF PDF cache')
class FanMechanicalLimitsTests(unittest.TestCase):
    def setUp(self):self.record=json.loads((ROOT/'sources/products/tcf-bc-sw-122.json').read_text())

    def test_independent_pdf_extraction_and_class_boundary(self):
        self.assertEqual(speed_table(self.record,PDF)['Class_I'],3167)
        self.assertEqual(evaluate(self.record,PDF,3167,'Class_I')['status'],'pass')
        self.assertEqual(evaluate(self.record,PDF,3168,'Class_I')['status'],'fail')
        self.assertEqual(evaluate(self.record,PDF,3500,'Class_II')['status'],'pass')

    def test_unknown_class_is_pending(self):
        r=evaluate(self.record,PDF,1450,None);self.assertEqual(r['status'],'pending');self.assertFalse(r['design_accepted'])

    def test_record_limit_tamper_is_not_authoritative(self):
        self.record['published_data']['maximum_speed_rpm']['Class_I']=9999
        with self.assertRaisesRegex(ProjectError,'independently extracted'):evaluate(self.record,PDF,3500,'Class_I')

    def test_wrong_product_and_invalid_speed_reject(self):
        for speed in (True,0,float('nan')):
            with self.assertRaises(ProjectError):evaluate(self.record,PDF,speed,'Class_I')
        self.record['product']['designation']='BC-DW 122'
        with self.assertRaises(ProjectError):evaluate(self.record,PDF,1450,'Class_I')

    def test_pdf_hash_tamper_rejects(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            path=Path(folder)/'source.pdf';path.write_bytes(PDF.read_bytes()+b'changed')
            with self.assertRaisesRegex(ProjectError,'pinned'):evaluate(self.record,path,1450,'Class_I')

    def test_actual_selected_curve_workflow_pass_fail_pending(self):
        runner=runpy.run_path(str(ROOT/'scripts/run_fan_mechanical_demo.py'))['run']
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'demo';r=runner(out,PDF)
            self.assertEqual([r['cases'][k]['mechanical'] for k in ('within','exceeded','unknown')],['pass','fail','pending'])
            for label in ('exceeded','unknown'):
                report=json.loads((out/label/'workflow/workflow.json').read_text())
                self.assertIn('required checks unresolved',report['tasks']['review']['scope'])
