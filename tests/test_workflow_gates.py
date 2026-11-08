import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,validate_plan,passages
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class WorkflowGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'project.json').write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
        brief=self.root/'brief.md';brief.write_text('Run declared checks before dependent authoring and review.')
        row=passages(brief)[0]
        tasks=[dict(id='check',kind='manual',description='Unresolved source applicability'),
               dict(id='independent',kind='electrical',project='project.json'),
               dict(id='drawing',kind='electrical',project='project.json',requires_pass=['check','independent']),
               dict(id='review',kind='manual',requires_pass=['drawing'])]
        self.plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},tasks=tasks,
                       requirements=[dict(id='R'+str(i),passage=row['id'],quote=row['text'],task=t['id'],acceptance=row['text']) for i,t in enumerate(tasks)])
        self.path=self.root/'plan.json'

    def save(self):self.path.write_text(json.dumps(self.plan))

    def test_pending_gate_skips_adapter_and_diagnoses_transitive_root(self):
        self.save()
        from bsa.cli import run
        with patch('bsa.cli.run',wraps=run) as adapter:
            r=execute(self.path,self.root/'run')
        self.assertEqual(adapter.call_count,1)
        self.assertEqual(r['tasks']['independent']['status'],'pass')
        self.assertEqual(r['tasks']['drawing']['status'],'pending')
        self.assertFalse((self.root/'run/drawing').exists())
        rows={r['id']:r for r in diagnose(self.path,self.root/'run')['tasks']}
        self.assertEqual(rows['drawing']['blocked_by'],['check'])
        self.assertEqual(rows['review']['upstream_action_tasks'],['check'])

    def test_passing_gates_allow_real_authoring(self):
        self.plan['tasks'][0]=dict(id='check',kind='electrical',project='project.json')
        self.save();r=execute(self.path,self.root/'run')
        self.assertEqual(r['tasks']['drawing']['status'],'pass')
        self.assertTrue((self.root/'run/drawing/devices.dxf').is_file())
        self.assertEqual(r['tasks']['review']['status'],'pending')
        self.assertFalse(r['design_accepted'])

    def test_failed_gate_is_not_bypassed(self):
        p=json.loads((self.root/'project.json').read_text());p['circuits'][0]['breaker_a']=.01
        (self.root/'failed.json').write_text(json.dumps(p))
        self.plan['tasks'][0]=dict(id='check',kind='electrical',project='failed.json')
        self.save();r=execute(self.path,self.root/'run')
        self.assertEqual(r['tasks']['check']['status'],'fail')
        self.assertEqual(r['tasks']['drawing']['status'],'pending')
        self.assertFalse((self.root/'run/drawing').exists())

    def test_unknown_future_self_duplicate_and_nonlist_gates_rejected(self):
        for gates in (['unknown'],['review'],['drawing'],['check','check'],'check',[{}]):
            self.plan['tasks'][2]['requires_pass']=gates;self.save()
            with self.subTest(gates=gates),self.assertRaisesRegex(ProjectError,'requires_pass'):validate_plan(self.path)
