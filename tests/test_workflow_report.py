import unittest
from bsa.engine import ProjectError
from bsa.workflow_report import render


class WorkflowReportTests(unittest.TestCase):
    def fixture(self,name='task/a #?.ifc'):
        return dict(inputs_unchanged=True,tasks={'task':{'status':'fail'}},artifact_hashes={name:'a'*64},
                    requirements=[dict(id='R1',task='task',quote='<script>alert(1)</script>',acceptance='Verify < 1 mm',
                        execution_status='fail',execution_scope='Diagnostic only',evidence=[name])])

    def test_encoded_artifact_links_and_escaped_requirements(self):
        text=render(self.fixture())
        self.assertIn('href="task/a%20%23%3F.ifc"',text)
        self.assertNotIn('<script>',text)
        self.assertIn('&lt;script&gt;',text)
        self.assertIn('Verify &lt; 1 mm',text)
        self.assertIn('diagnostic artifacts',text)
        self.assertIn('Acceptance: pending review',text)

    def test_unsafe_or_untracked_artifacts_rejected(self):
        for name in ('../escape','/absolute','C:/path','task\\escape','https://example.com/a'):
            with self.assertRaises(ProjectError):render(self.fixture(name))
        report=self.fixture();report['artifact_hashes']={}
        with self.assertRaisesRegex(ProjectError,'manifest'):render(report)
