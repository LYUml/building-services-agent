import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.workflow import validate_plan
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'runs/public-brief-intake-v1/sources'
REVIEW=ROOT/'benchmarks/mit-4401-2018/source-review.json'

@unittest.skipUnless((CACHE/'course-project.pdf').is_file(),'requires pinned public source cache')
class PublicBriefReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.module=runpy.run_path(str(ROOT/'scripts/stage_public_brief_benchmark.py'))

    def test_review_preserves_all_technical_passages_and_interpretation_blockers(self):
        result=self.module['run'](self.root/'case',CACHE,True)
        plan=self.root/'case/plan.json';p,_=validate_plan(plan)
        technical={id for id,value in p['passage_dispositions'].items() if value=='requirement'}
        self.assertEqual(len(p['passage_dispositions']),41);self.assertEqual(len(technical),34)
        self.assertEqual({r['passage'] for r in p['requirements']},technical)
        self.assertEqual(len(p['unresolved_inputs']),34);self.assertEqual(result['review_notes_applied'],29)
        self.assertFalse(result['design_accepted'])

    def test_incomplete_review_and_technical_context_forgery_reject(self):
        self.module['run'](self.root/'case',CACHE)
        plan=self.root/'case/plan.json';original=plan.read_bytes()
        review=json.loads(REVIEW.read_text());review['issue_notes'].pop(next(iter(review['issue_notes'])))
        file=self.root/'incomplete.json';file.write_text(json.dumps(review))
        with self.assertRaisesRegex(ProjectError,'identity differs'):self.module['apply_source_review'](plan,file)
        self.assertEqual(plan.read_bytes(),original)
        review=json.loads(REVIEW.read_text());review['context_passages']['P001']='pretend technical content is boilerplate';review['context_passage_text_sha256']['P001']='wrong'
        file.write_text(json.dumps(review))
        with self.assertRaisesRegex(ProjectError,'boilerplate'):self.module['apply_source_review'](plan,file)
        self.assertEqual(plan.read_bytes(),original)
