import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,passages,validate_plan,verify

ROOT=Path(__file__).resolve().parents[1]


class WaterWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ('network','bases'):shutil.copyfile(ROOT/('examples/regulations-hk-water/'+name+'.json'),self.root/(name+'.json'))
        pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
        pdf=self.root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
        pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
        (self.root/'pack.json').write_text(json.dumps(pack))
        brief=self.root/'brief.md';brief.write_text('Check water piping.\n\nRun the same network after checks.')
        rows=passages(brief)
        tasks=[dict(id='rules',kind='water_pipe_regulations',project='network.json',basis='bases.json',pack='pack.json',sources='.'),dict(id='network',kind='network',project='network.json',requires_pass=['rules'])]
        self.plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,requirements=[dict(id=str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
        self.path=self.root/'plan.json';self.save()

    def save(self):self.path.write_text(json.dumps(self.plan))

    def test_passing_sources_bind_and_execute(self):
        r=execute(self.path,self.root/'run')
        self.assertEqual(r['tasks']['rules']['status'],'pass')
        self.assertEqual(r['tasks']['network']['status'],'pass')
        self.assertTrue(verify(self.root/'run')['integrity_pass']);self.assertFalse(r['design_accepted'])

    def test_different_network_bytes_rejected(self):
        p=json.loads((self.root/'network.json').read_text());p['supply']['total_pressure_pa']+=1
        (self.root/'different.json').write_text(json.dumps(p))
        self.plan['tasks'][1]['project']='different.json';self.save()
        with self.assertRaisesRegex(ProjectError,'different network bytes'):validate_plan(self.path)

    def test_hydraulic_failure_blocks_downstream(self):
        p=json.loads((self.root/'network.json').read_text());p['supply']['total_pressure_pa']=0
        (self.root/'network.json').write_text(json.dumps(p))
        r=execute(self.path,self.root/'run')
        self.assertEqual(r['tasks']['rules']['status'],'fail')
        self.assertEqual(r['tasks']['network']['status'],'pending')
        self.assertFalse((self.root/'run/network').exists())

    def test_changed_official_source_blocks_downstream(self):
        (self.root/'emsd-bec-2024.pdf').write_bytes(b'changed')
        r=execute(self.path,self.root/'run')
        self.assertEqual(r['tasks']['rules']['status'],'pending')
        self.assertEqual(r['tasks']['network']['status'],'pending')


if __name__=='__main__':unittest.main()
