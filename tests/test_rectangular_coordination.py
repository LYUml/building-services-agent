import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.workflow import execute
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'


class RectangularCoordinationTests(unittest.TestCase):
    def test_actual_selected_model_clear_and_intrusion_cases(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            for label,expected in (('clearance','pass'),('intrusion','fail')):
                out=Path(folder)/label;plan=EX/f'{label}-plan.json';execute(plan,out)
                rows=diagnose(plan,out)['tasks']
                self.assertEqual([r['status'] for r in rows],['pass',expected,'pending'])
                report=json.loads((out/'coordination/clash.json').read_text())
                from bsa.cli import digest
                model=out/'air/selected-coordination/bim/model.ifc'
                self.assertEqual(report['inputs'][str(model)],digest(model))
                if expected=='fail':self.assertEqual(rows[-1]['blocked_by'],['coordination'])

    def test_producer_byte_change_during_clash_cannot_pass(self):
        from bsa.clash import run as real
        def altered(source,*args):
            path=Path(source);path.write_bytes(path.read_bytes()+b'\n')
            return real(source,*args)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'run';plan=EX/'clearance-plan.json'
            with patch('bsa.clash.run',side_effect=altered):execute(plan,out)
            report=json.loads((out/'workflow.json').read_text())
            self.assertEqual(report['tasks']['coordination']['status'],'fail')
            self.assertIn('artifacts changed',report['tasks']['coordination']['scope'])
            self.assertEqual(report['tasks']['review']['status'],'fail')
            self.assertIn('artifacts changed',report['tasks']['review']['scope'])
