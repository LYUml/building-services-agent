import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from bsa.energy import validate,run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/"examples/two-zone-energy/project.json"

class EnergyTests(unittest.TestCase):
    def test_rejects_invalid_physics(self):
        p=json.loads(PROJECT.read_text())
        for field,value in (("height_m",0),("baseline_lighting_w_m2",-1),("cooling_setpoint_c",float("nan"))):
            q=copy.deepcopy(p);q[field]=value
            with self.assertRaises(ProjectError):validate(q)
        q=copy.deepcopy(p);q["design_days"][0]["wet_bulb_c"]=80
        with self.assertRaises(ProjectError):validate(q)

    @unittest.skipUnless(os.environ.get("BSA_TEST_ENERGYPLUS"),"requires explicit EnergyPlus executable")
    def test_real_engine_geometry_and_lighting_balance(self):
        root=ROOT/"runs";root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            r=run(PROJECT,Path(folder)/"energy",Path(os.environ["BSA_TEST_ENERGYPLUS"]))
            self.assertTrue(r["input_unchanged"])
            self.assertFalse(r["design_accepted"])
            for variant,power in (("baseline",0.48),("variant",0.24)):
                result=r["results"][variant]
                self.assertEqual(result["metadata"]["thermal_zones"],2)
                self.assertEqual(result["metadata"]["floor_area_m2"],40)
                self.assertEqual(result["metadata"]["matched_surface_count"],2)
                for row in result["whole_building"]:
                    if row["variable"]=="Lights Electricity Rate":
                        self.assertAlmostEqual(row["coincident_peak_kw"],power)
                        self.assertAlmostEqual(row["simulated_period_kwh"],power*24)
                        self.assertEqual(row["samples"],24)
            summer=[x for x in r["comparison"] if x["environment"]=="SYNTHETIC SUMMER" and "Cooling Rate" in x["variable"]]
            self.assertEqual(len(summer),1)
            self.assertLess(summer[0]["peak_change_kw"],0)

if __name__=="__main__":unittest.main()
