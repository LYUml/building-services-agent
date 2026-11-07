import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.engine import validate, calculate, ProjectError
from bsa.cli import run

EXAMPLE=Path(__file__).resolve().parents[1]/"examples/office-electrical/project.json"

class ElectricalTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(EXAMPLE.read_text())

    def test_independent_hand_calculation(self):
        r=calculate(self.p);c=r["circuits"][0]
        self.assertAlmostEqual(c["connected_electrical_kw"],0.12)
        self.assertAlmostEqual(c["design_current_a"],120/0.9/230)
        self.assertAlmostEqual(c["effective_ampacity_a"],14.4)
        self.assertAlmostEqual(c["voltage_drop_v"],29*(120/0.9/230)*20/1000)
        self.assertFalse(r["design_accepted"])

    def test_rejects_invalid_provenance_and_topology(self):
        for mutate in (lambda p:p["devices"][0].update(circuit="missing"),
                       lambda p:p["devices"][0].update(source="missing"),
                       lambda p:p["devices"][0].update(power_factor=0),
                       lambda p:p["devices"][0].update(electrical_kw=float("nan")),
                       lambda p:p["circuits"][0].update(breaker_a=True),
                       lambda p:p["devices"].append(copy.deepcopy(p["devices"][0]))):
            p=copy.deepcopy(self.p);mutate(p)
            with self.assertRaises(ProjectError):validate(p)

    def test_failed_cable_checks_are_visible(self):
        self.p["circuits"][0].update(tabulated_ampacity_a=1, route_length_m=10000)
        r=calculate(self.p)
        self.assertFalse(r["calculated_checks_pass"])
        self.assertFalse(r["circuits"][0]["checks"]["in_le_iz"])
        self.assertFalse(r["circuits"][0]["checks"]["voltage_drop"])

    def test_artifacts_and_source_preservation(self):
        before=EXAMPLE.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/"run"
            run(EXAMPLE,out)
            m=json.loads((out/"manifest.json").read_text())
            self.assertEqual(m["device_count"],3)
            self.assertEqual(m["dxf_circle_count"],3)
            self.assertEqual(EXAMPLE.read_bytes(),before)
            self.assertIn("report.html",m["outputs"])
            with self.assertRaises(FileExistsError):run(EXAMPLE,out)

if __name__=="__main__":unittest.main()
