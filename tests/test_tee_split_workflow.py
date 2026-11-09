import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.workflow import execute,validate_plan,verify
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]

class SplitWorkflowTests(unittest.TestCase):
    def test_failures_block_consumers_and_source_substitution(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for path in (ROOT/'examples/tee-trial').glob('*'):
                if path.is_file():shutil.copyfile(path,root/path.name)
            plan=json.loads((root/'split-plan.json').read_text())
            plan['tasks'].append(dict(id='diagnostic',kind='tee_losses',depends_on='assembly',basis='loss-basis.json',requires_pass=['split']))
            req=dict(plan['requirements'][-1]);req.update(id='diagnostic',task='diagnostic');plan['requirements'].append(req)
            p=root/'plan.json';p.write_text(json.dumps(plan))
            basis=root/'split-basis.json';original=json.loads(basis.read_text())
            for label in ('capacity','no-root'):
                data=json.loads(json.dumps(original))
                if label=='capacity':data['inlet_total_pressure_pa']=499
                else:data['required_outlet_total_pressure_pa']['branch']=10000
                basis.write_text(json.dumps(data));result=execute(p,root/label)
                self.assertEqual(result['tasks']['split']['status'],'fail')
                self.assertEqual(result['tasks']['diagnostic']['status'],'pending')
                self.assertFalse((root/label/'diagnostic').exists())
                self.assertTrue(verify(root/label)['integrity_pass'])
            plan['tasks'][1]['ifc']='replacement.ifc';p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ProjectError,'replacement'):validate_plan(p)
            del plan['tasks'][1]['ifc']
            # A successful split must not gate an unrelated IFC producer.
            extra=dict(plan['tasks'][0]);extra['id']='other';plan['tasks'].insert(1,extra)
            req=dict(plan['requirements'][0]);req.update(id='other',task='other');plan['requirements'].append(req)
            plan['tasks'][-1]['depends_on']='other';p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ProjectError,'different model'):validate_plan(p)

if __name__=='__main__':unittest.main()
