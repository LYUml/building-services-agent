import json
from pathlib import Path
import shutil
import tempfile
import unittest
import ifcopenshell
from bsa.tee_selection import run,prepare
ROOT=Path(__file__).resolve().parents[1]
class TeeSelectionTests(unittest.TestCase):
    def test_selection_replay_no_feasible_and_changed_duty(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);shutil.copytree(ROOT/'examples/tee-trial',root/'inputs');catalogue=root/'inputs/selection-catalogue.json'
            result=run(catalogue,root/'positive')
            self.assertEqual(result['selected'],'bore40');self.assertTrue(result['selected_rerun_pass'])
            self.assertFalse(result['trials'][0]['passed']);self.assertFalse(result['trials'][0]['details']['checks']['source_pressure_capacity'])
            a=ifcopenshell.open(str(root/'positive/candidates/bore32/assembly/assembly.ifc'))
            b=ifcopenshell.open(str(root/'positive/selected/assembly/assembly.ifc'))
            for cls in ('IfcPipeSegment','IfcPipeFitting','IfcDistributionPort'):
                self.assertEqual({e.GlobalId for e in a.by_type(cls)},{e.GlobalId for e in b.by_type(cls)})
            data=json.loads(catalogue.read_text());data['candidates']=data['candidates'][:1];catalogue.write_text(json.dumps(data))
            failed=run(catalogue,root/'none');self.assertIsNone(failed['selected']);self.assertFalse(failed['calculated_checks_pass']);self.assertFalse((root/'none/selected').exists())
            data=json.loads((ROOT/'examples/tee-trial/selection-catalogue.json').read_text())
            basis=json.loads((root/'inputs/selection/basis.json').read_text());basis['inlet_total_pressure_pa']=1000
            (root/'inputs/selection/changed.json').write_text(json.dumps(basis));data['candidates'][1]['basis']='selection/changed.json';catalogue.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'common duty'):prepare(catalogue)
if __name__=='__main__':unittest.main()
