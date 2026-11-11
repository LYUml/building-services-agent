import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bsa.engine import ProjectError
from bsa.work_plan_review import template,apply
from bsa.workflow import validate_plan,execute
from bsa.workflow_draft import draft
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class WorkPlanCLITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.plan=self.root/'plan.json';self.review=self.root/'review.json'
        (self.root/'brief.md').write_text('Design supply air distribution.\n\nReport thermal kW separately from electrical kW.\n',encoding='utf-8')
        (self.root/'rubric.md').write_text('提供可编辑图纸和计算报告。',encoding='utf-8')
        draft(self.root/'brief.md',self.plan,[self.root/'rubric.md'])

    def fill(self):
        template(self.plan,self.review)
        row=json.loads(self.review.read_text(encoding='utf-8'))
        row['tasks']=[dict(id='hvac',description='Design source-backed HVAC distribution and report',
            blocker='Geometry, load assumptions and actual equipment remain to be reviewed',
            acceptance='Editable drawing and independently checked calculations against all original obligations',requires_pass=[])]
        for item in row['passages'].values():item['tasks']=['hvac']
        self.review.write_text(json.dumps(row,ensure_ascii=False),encoding='utf-8')
        return row

    def test_template_preserves_bundle_quotes_and_cannot_apply_uninterpreted(self):
        result=template(self.plan,self.review);record=json.loads(self.review.read_text(encoding='utf-8'))
        self.assertEqual(result['technical_passages'],3)
        self.assertEqual(record['source_passages'][-1]['text'],'提供可编辑图纸和计算报告。')
        self.assertIn('D002:P001',record['passages']);self.assertEqual(record['tasks'],[])
        with self.assertRaises(ProjectError):apply(self.plan,self.review,self.root/'interpreted.json')
        self.assertFalse((self.root/'interpreted.json').exists())

    def test_new_plan_retains_original_and_pending_execution(self):
        self.fill();original=self.plan.read_bytes();source=json.loads(original)
        out=self.root/'interpreted.json';apply(self.plan,self.review,out)
        current,inputs=validate_plan(out)
        self.assertEqual(self.plan.read_bytes(),original)
        self.assertEqual({(r['passage'],r['quote']) for r in current['requirements']},{(r['passage'],r['quote']) for r in source['requirements']})
        self.assertIn(self.review,inputs)
        execute(out,self.root/'run');status=diagnose(out,self.root/'run')
        self.assertEqual(len(status['actions']),1);self.assertTrue(status['actions'][0]['input_blockers'])
        saved=out.read_bytes()
        with self.assertRaises(ProjectError):apply(self.plan,self.review,out)
        self.assertEqual(out.read_bytes(),saved)

    def test_missing_passage_and_source_mutation_leave_no_new_plan(self):
        row=self.fill();out=self.root/'interpreted.json'
        broken=copy.deepcopy(row);broken['passages'].pop('D002:P001')
        self.review.write_text(json.dumps(broken),encoding='utf-8')
        with self.assertRaises(ProjectError):apply(self.plan,self.review,out)
        self.assertFalse(out.exists())
        self.review.write_text(json.dumps(row),encoding='utf-8')
        (self.root/'rubric.md').write_text('Different obligations',encoding='utf-8')
        with self.assertRaises(ProjectError):apply(self.plan,self.review,out)
        self.assertFalse(out.exists())

    def test_cli_template_and_apply_emit_pending_json_without_replacing_original(self):
        def cli(*args):return subprocess.run([sys.executable,'-m','bsa.work_plan_review',*map(str,args)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        result=cli('template',self.plan,'--out',self.review)
        self.assertEqual(result.returncode,2,result.stderr);self.assertFalse(json.loads(result.stdout)['design_accepted'])
        self.review.unlink();self.fill();before=self.plan.read_bytes();out=self.root/'interpreted.json'
        result=cli('apply',self.plan,self.review,'--out',out)
        self.assertEqual(result.returncode,2,result.stderr);self.assertEqual(json.loads(result.stdout)['reviewed_work_packages'],1)
        self.assertEqual(self.plan.read_bytes(),before);validate_plan(out)

    def test_different_output_directory_and_existing_review_reject(self):
        self.fill()
        with self.assertRaises(ProjectError):template(self.plan,self.review)
        with self.assertRaises(ProjectError):apply(self.plan,self.review,self.root/'nested/new.json')
