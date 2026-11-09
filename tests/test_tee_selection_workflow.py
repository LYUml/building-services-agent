import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.workflow import execute,verify
ROOT=Path(__file__).resolve().parents[1]
class SelectionWorkflowTests(unittest.TestCase):
    def test_no_feasible_blocks_selected_drawing_and_native(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);shutil.copytree(ROOT/'examples/tee-trial',root/'inputs');catalogue=root/'inputs/selection-catalogue.json'
            data=json.loads(catalogue.read_text());data['candidates']=data['candidates'][:1];catalogue.write_text(json.dumps(data))
            report=execute(root/'inputs/selection-plan.json',root/'blocked')
            self.assertEqual(report['tasks']['selection']['status'],'fail')
            for name in ('drawing','native'):
                self.assertEqual(report['tasks'][name]['status'],'pending');self.assertFalse((root/'blocked'/name).exists())
            self.assertTrue(verify(root/'blocked')['integrity_pass'])
if __name__=='__main__':unittest.main()
