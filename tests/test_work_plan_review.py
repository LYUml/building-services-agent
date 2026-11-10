import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.work_plan_review import apply
from bsa.workflow import validate_plan
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'runs/public-brief-intake-v1/sources'

@unittest.skipUnless((CACHE/'assignment5.pdf').is_file(),'requires pinned official public source cache')
class WorkPlanReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'case'
        runpy.run_path(str(ROOT/'scripts/stage_public_brief_benchmark.py'))['run'](self.root,CACHE,True)
        self.plan=self.root/'plan.json';self.review=self.root/'work-plan-review.json'
        self.review.write_bytes((ROOT/'benchmarks/mit-4401-2018/work-plan-review.json').read_bytes())

    def test_review_retains_every_original_quote_and_inventories_the_record(self):
        old=json.loads(self.plan.read_text(encoding='utf-8'));result=apply(self.plan,self.review)
        new,inputs=validate_plan(self.plan)
        self.assertEqual(result['technical_passages'],34);self.assertEqual(result['reviewed_work_packages'],14)
        self.assertEqual(new['passage_dispositions'],old['passage_dispositions'])
        self.assertEqual({(r['passage'],r['quote']) for r in new['requirements']},{(r['passage'],r['quote']) for r in old['requirements']})
        self.assertEqual(len(new['unresolved_inputs']),14)
        self.assertTrue(all(t['kind']=='manual' for t in new['tasks']))
        self.assertIn(self.review,inputs);self.assertFalse(result['design_accepted'])

    def test_loss_text_drift_unknown_task_and_source_forgery_are_transactional(self):
        original=self.plan.read_bytes();review=json.loads(self.review.read_text(encoding='utf-8'))
        for mode in ('missing','text','task','source','cycle'):
            row=copy.deepcopy(review)
            if mode=='missing':row['passages'].pop('D005:P007')
            if mode=='text':row['passages']['D005:P007']['text_sha256']='wrong'
            if mode=='task':row['passages']['D005:P007']['tasks']=['not-reviewed']
            if mode=='source':row['source_sha256']['sources/assignment5.pdf']='wrong'
            if mode=='cycle':row['tasks'][0]['requires_pass']=['presentation']
            self.review.write_text(json.dumps(row),encoding='utf-8')
            with self.subTest(mode=mode),self.assertRaises(ProjectError):apply(self.plan,self.review)
            self.assertEqual(self.plan.read_bytes(),original)
            self.assertFalse((self.root/'work-plan-candidate.json').exists())

    def test_declared_engineering_gap_cannot_be_erased_by_scaffold_review(self):
        row=json.loads(self.plan.read_text(encoding='utf-8'))
        row['unresolved_inputs'][0]['description']='Actual engineering fact is missing, not merely interpretation'
        self.plan.write_text(json.dumps(row),encoding='utf-8');before=self.plan.read_bytes()
        with self.assertRaisesRegex(ProjectError,'unrelated unresolved'):apply(self.plan,self.review)
        self.assertEqual(self.plan.read_bytes(),before)
