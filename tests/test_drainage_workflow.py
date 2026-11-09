import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.workflow import execute, verify
from bsa.delivery import template, assess
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class DrainageWorkflowTests(unittest.TestCase):
    def test_preparation_cannot_complete_hydraulic_requirement(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);plan=ROOT/'examples/drainage-preparation/plan.json'
            result=execute(plan,root/'run')
            self.assertEqual(result['tasks']['prepare']['status'],'pass')
            self.assertEqual(result['tasks']['hydraulic-review']['status'],'pending')
            self.assertFalse(result['execution_pass'])
            self.assertTrue(verify(root/'run')['integrity_pass'])
            review=root/'review.json';template(plan,root/'run',review)
            self.assertEqual(assess(plan,root/'run',review)['status'],'needs_review')
            report=json.loads((root/'run/prepare/preparation.json').read_text())
            self.assertFalse(report['simulation_executed'])

    def test_bad_geometry_blocks_downstream_and_changed_source_invalidates_run(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples/drainage-preparation',root/'input')
            project=root/'input/project.json';data=json.loads(project.read_text())
            data['conduits'][0]['outlet_offset_m']=1;project.write_text(json.dumps(data))
            plan=root/'input/plan.json';result=execute(plan,root/'run')
            self.assertEqual(result['tasks']['prepare']['status'],'fail')
            rows={r['id']:r for r in diagnose(plan,root/'run')['tasks']}
            self.assertEqual(rows['hydraulic-review']['blocked_by'],['prepare'])
            self.assertFalse((root/'run/prepare/network.inp').exists())
            project.write_text(project.read_text()+'\n')
            self.assertFalse(verify(root/'run')['integrity_pass'])


if __name__=='__main__':unittest.main()
