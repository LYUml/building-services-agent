import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,verify,validate_plan
from bsa.delivery import context,template,assess

ROOT=Path(__file__).resolve().parents[1]

class SupportingEvidenceTests(unittest.TestCase):
    def fixture(self,root):
        shutil.copyfile(ROOT/'examples/office-electrical/project.json',root/'project.json')
        brief=root/'brief.md';brief.write_text('Calculate and review the complete design.')
        plan=dict(version=1,brief=brief.name,brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
            tasks=[dict(id='calculation',kind='electrical',project='project.json'),dict(id='review',kind='manual',description='Physical design review pending')],
            requirements=[dict(id='R1',passage='P001',quote=brief.read_text(),task='calculation',acceptance='Conditional calculation'),
                dict(id='R2',passage='P001',quote=brief.read_text(),task='review',supporting_tasks=['calculation'],acceptance='Full source obligation remains pending')])
        path=root/'plan.json';path.write_text(json.dumps(plan));return path

    def test_actual_calculation_supports_pending_requirement_without_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan=self.fixture(root);out=root/'run';result=execute(plan,out)
            row=result['requirements'][1];support=row['supporting_evidence']['calculation']
            self.assertEqual(row['execution_status'],'pending');self.assertEqual(row['evidence'],[])
            self.assertEqual(support['status'],'pass');self.assertIn('calculation/calculations.json',support['evidence'])
            self.assertFalse(result['design_accepted']);self.assertTrue(verify(out)['integrity_pass']);context(plan,out)
            text=(out/'index.html').read_text();self.assertIn('Related evidence; primary acceptance remains pending',text)
            review=root/'review.json';template(plan,out,review);audit=assess(plan,out,review)
            self.assertEqual(audit['requirements'][1]['effective_review_status'],'pending')

    def test_common_requirements_provider_preserves_support_bindings(self):
        from bsa.modules import run as run_module,verify_result
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);plan=self.fixture(root)
            request=root/'request.json';request.write_text(json.dumps(dict(schema='bsa.module-request/1',project_id='support-test',scenario_id='pending-review',capability='requirements.source-inventory',coordinate_frame=dict(id='source-only',kind='source-world-si',length_unit='m',georeferenced=False),sources=dict(plan=dict(path=plan.name,sha256=digest(plan))))))
            result=run_module(request,'bsa.source-requirements',root/'inventory');verify_result(root/'inventory/result.json')
            self.assertEqual(result['payload']['requirements'][1]['supporting_tasks'],['calculation'])
            out=root/'run';execute(plan,out,requirements_result=root/'inventory/result.json')
            self.assertTrue(verify(out)['integrity_pass']);context(plan,out)

    def test_failed_support_retains_failed_status_and_pending_primary(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan=self.fixture(root);project=root/'project.json';d=json.loads(project.read_text());d['circuits'][0]['breaker_a']=.1;project.write_text(json.dumps(d))
            result=execute(plan,root/'run');row=result['requirements'][1]
            self.assertEqual(row['supporting_evidence']['calculation']['status'],'fail');self.assertEqual(row['execution_status'],'pending')

    def test_invalid_unknown_duplicate_and_primary_support_reject(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=self.fixture(root);original=json.loads(path.read_text())
            for value in [['missing'],['calculation','calculation'],['review'],'calculation']:
                data=json.loads(json.dumps(original));data['requirements'][1]['supporting_tasks']=value;path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):validate_plan(path)

    def test_forged_support_or_omitted_binding_rejects_source_and_delivery_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan=self.fixture(root);out=root/'run';execute(plan,out);path=out/'workflow.json';original=path.read_bytes()
            for action in ['status','files','omit','tasks']:
                report=json.loads(original);row=report['requirements'][1]
                if action=='status':row['supporting_evidence']['calculation']['status']='pending'
                if action=='files':row['supporting_evidence']['calculation']['evidence']=[]
                if action=='omit':row.pop('supporting_evidence')
                if action=='tasks':row['supporting_tasks']=[]
                path.write_text(json.dumps(report));self.assertFalse(verify(out)['integrity_pass'],action)
                with self.assertRaises(ValueError):context(plan,out)

if __name__=='__main__':unittest.main()
