import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute, passages, validate_plan, verify

ROOT=Path(__file__).resolve().parents[1]


class CirculationWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for name in ('project.json','thermal-duty.json','thermal-duty-insufficient.json'):
            shutil.copyfile(ROOT/'examples/hvac-circulation'/name,self.root/name)
        brief=self.root/'brief.md';brief.write_text('Check sourced thermal duty.\n\nRelease the same hydraulic scenario only after passing duty checks.')
        rows=passages(brief)
        tasks=[dict(id='duty',kind='circulation_duty',project='project.json',basis='thermal-duty.json'),dict(id='water',kind='water_network',project='project.json',requires_pass=['duty'])]
        self.plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,requirements=[dict(id=str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
        self.path=self.root/'plan.json'

    def save(self):self.path.write_text(json.dumps(self.plan))

    def test_pass_and_integrity(self):
        self.save();r=execute(self.path,self.root/'run')
        self.assertEqual(r['tasks']['duty']['status'],'pass')
        self.assertEqual(r['tasks']['water']['status'],'pass')
        self.assertTrue(verify(self.root/'run')['integrity_pass'])
        (self.root/'thermal-duty.json').write_text('{}')
        self.assertFalse(verify(self.root/'run')['integrity_pass'])

    def test_insufficient_duty_blocks(self):
        self.plan['tasks'][0]['basis']='thermal-duty-insufficient.json';self.save()
        r=execute(self.path,self.root/'run')
        self.assertEqual(r['tasks']['duty']['status'],'fail')
        self.assertEqual(r['tasks']['water']['status'],'pending')
        self.assertFalse((self.root/'run/water').exists())

    def test_changed_downstream_network_rejected(self):
        p=json.loads((self.root/'project.json').read_text());p['pipes'][1]['length_m']+=1
        (self.root/'changed.json').write_text(json.dumps(p))
        self.plan['tasks'][1]['project']='changed.json';self.save()
        with self.assertRaisesRegex(ProjectError,'different circulation bytes'):validate_plan(self.path)


if __name__=='__main__':unittest.main()
