import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.workflow import execute,validate_plan
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]
class TeeDrawingWorkflowTests(unittest.TestCase):
    def test_failed_split_blocks_dxf_and_native_and_unrelated_model(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for p in (ROOT/'examples/tee-trial').glob('*'):
                if p.is_file():shutil.copyfile(p,root/p.name)
            basis=root/'split-basis.json';data=json.loads(basis.read_text());data['inlet_total_pressure_pa']=499;basis.write_text(json.dumps(data))
            plan=root/'drawing-plan.json';report=execute(plan,root/'blocked')
            self.assertEqual(report['tasks']['split']['status'],'fail')
            for name in ('drawing','native'):
                self.assertEqual(report['tasks'][name]['status'],'pending');self.assertFalse((root/'blocked'/name).exists())
            p=json.loads(plan.read_text());extra=dict(p['tasks'][0]);extra['id']='other';p['tasks'].insert(1,extra)
            req=dict(p['requirements'][0]);req.update(id='other',task='other');p['requirements'].append(req)
            next(t for t in p['tasks'] if t['id']=='drawing')['depends_on']='other';plan.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError,'different model'):validate_plan(plan)
if __name__=='__main__':unittest.main()
