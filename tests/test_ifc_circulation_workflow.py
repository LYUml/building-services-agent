import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,verify,passages,validate_plan
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class IFCWorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        for name in ('model.json','project.json','binding.json','regulatory-bases.json'):
            shutil.copyfile(ROOT/'examples/circulation-ifc'/name,self.root/name)
        shutil.copyfile(ROOT/'examples/hvac-circulation/thermal-duty.json',self.root/'thermal.json')
        pdf=self.root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
        pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text());pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
        (self.root/'pack.json').write_text(json.dumps(pack))
        brief=self.root/'brief.md';brief.write_text('Author synthetic IFC.\n\nBind native hydraulic geometry.\n\nCheck thermal duty and pipe rules.\n\nReview complete engineering acceptance.')
        rows=passages(brief)
        tasks=[dict(id='model',kind='bim',project='model.json'),dict(id='water',kind='water_coordination',project='project.json',binding='binding.json',depends_on='model'),dict(id='checks',kind='ifc_circulation_checks',depends_on='water',thermal_basis='thermal.json',rule_basis='regulatory-bases.json',pack='pack.json',sources='.'),dict(id='review',kind='manual',description='Full acceptance pending',requires_pass=['checks'])]
        self.plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,requirements=[dict(id=str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
        self.path=self.root/'plan.json'

    def save(self):self.path.write_text(json.dumps(self.plan))

    def test_positive_and_thermal_failure(self):
        self.save();r=execute(self.path,self.root/'pass')
        for id in ('model','water','checks'):self.assertEqual(r['tasks'][id]['status'],'pass')
        self.assertTrue(verify(self.root/'pass')['integrity_pass']);self.assertFalse(r['design_accepted'])
        b=json.loads((self.root/'thermal.json').read_text());b['targets'][0]['thermal_power']['value']=1000
        (self.root/'thermal.json').write_text(json.dumps(b))
        r=execute(self.path,self.root/'fail')
        self.assertEqual(r['tasks']['water']['status'],'pass')
        self.assertEqual(r['tasks']['checks']['status'],'fail')
        self.assertIn('required checks unresolved',r['tasks']['review']['scope'])

    def test_replacement_and_wrong_producer_rejected(self):
        self.plan['tasks'][2]['project']='project.json';self.save()
        with self.assertRaisesRegex(ProjectError,'replacements forbidden'):validate_plan(self.path)
        del self.plan['tasks'][2]['project'];self.plan['tasks'][2]['depends_on']='model';self.save()
        with self.assertRaisesRegex(ProjectError,'earlier water_coordination'):validate_plan(self.path)
