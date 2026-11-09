import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.workflow import execute,validate_plan,verify
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]

class TeeWorkflowTests(unittest.TestCase):
    def test_execution_failure_blocking_and_no_replacement(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for p in (ROOT/'examples/tee-trial').glob('*'):
                if p.is_file():shutil.copyfile(p,root/p.name)
            plan=root/'plan.json'
            result=execute(plan,root/'positive')
            self.assertTrue(result['execution_pass'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            p=json.loads(plan.read_text());p['tasks'][1]['tee_spec']='spec.json';plan.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError,'replacement'):validate_plan(plan)
            del p['tasks'][1]['tee_spec'];plan.write_text(json.dumps(p))
            spec=root/'spec.json';data=json.loads(spec.read_text());data['inner_radius_m']=1;spec.write_text(json.dumps(data))
            result=execute(plan,root/'blocked')
            self.assertEqual(result['tasks']['assembly']['status'],'fail')
            self.assertEqual(result['tasks']['coefficients']['status'],'pending')
            self.assertFalse((root/'blocked/coefficients').exists())

if __name__=='__main__':unittest.main()

