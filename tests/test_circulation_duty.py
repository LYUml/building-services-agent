import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.circulation_duty import validate, evaluate, run
from bsa.engine import ProjectError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT/'examples/hvac-circulation'


class ThermalDutyTests(unittest.TestCase):
    def test_contract(self):
        p = json.loads((EXAMPLE/'project.json').read_text())
        b = json.loads((EXAMPLE/'thermal-duty.json').read_text())
        validate(b, p)
        for key, value in [('unit', 'kW'), ('value', 0), ('value', True), ('value', float('nan')), ('source', 'missing')]:
            changed = copy.deepcopy(b)
            changed['targets'][0]['thermal_power'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ProjectError):
                validate(changed, p)
        b['targets'][0]['link'] = 'REFERENCE'
        with self.assertRaises(ProjectError): validate(b, p)

    def test_direction_and_hydraulic_failure(self):
        b = json.loads((EXAMPLE/'thermal-duty.json').read_text())
        for flow, hydraulics in [(-.01, True), (.01, False)]:
            result = evaluate(b, {'pipes':[{'id':'OUTBOUND', 'flow_m3_s':flow}], 'calculated_checks_pass':hydraulics})
            self.assertFalse(result['calculated_checks_pass'])

    def test_actual_engine_pass_and_insufficient_duty(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            for filename, expected in [('thermal-duty.json', True), ('thermal-duty-insufficient.json', False)]:
                result = run(EXAMPLE/'project.json', EXAMPLE/filename, Path(tmp)/filename)
                self.assertTrue(result['hydraulic_checks_pass'])
                self.assertEqual(result['calculated_checks_pass'], expected)
                row = result['targets'][0]
                self.assertAlmostEqual(row['required_flow_m3_s'], (.04 if expected else .1)/20.9, places=12)
                self.assertAlmostEqual(row['directed_flow_m3_s'], .0030373088, delta=1e-7)
                self.assertFalse(result['design_accepted'])


if __name__ == '__main__': unittest.main()
