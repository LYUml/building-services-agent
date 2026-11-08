import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.regulation_coverage import run
from bsa.workflow import passages

ROOT=Path(__file__).resolve().parents[1]


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'regulations/hk',self.root/'hk')
        self.catalog=self.root/'hk/coverage-2026.11.08.json'
        self.scope=self.root/'scope.json'
        self.data=json.loads((ROOT/'examples/regulations-hk/coverage-scope.json').read_text())
        self.save()

    def save(self):self.scope.write_text(json.dumps(self.data))
    def check(self,plan=None):return run(self.catalog,self.scope,self.root/'out',plan)

    def test_unimplemented_and_unscheduled_are_distinct(self):
        r=self.check();rows={t['id']:t for t in r['topics']}
        self.assertEqual(rows['plumbing']['gaps'],['no_implemented_module'])
        self.assertIn('implemented_module_not_scheduled',rows['hvac']['gaps'])
        self.assertEqual(rows['utility']['gaps'],['applicability_unresolved'])
        self.assertFalse(r['coverage_complete']);self.assertFalse(r['design_accepted'])

    def test_silent_omission_and_unsourced_exclusion_rejected(self):
        original=json.loads(json.dumps(self.data))
        for change in ('missing','unsourced','reason'):
            self.data=json.loads(json.dumps(original))
            if change=='missing':del self.data['topics']['fire']
            elif change=='unsourced':self.data['topics']['fire']['source']=''
            else:self.data['topics']['fire']['decision']='excluded'
            self.save()
            with self.subTest(change=change),self.assertRaises(ProjectError):self.check()

    def test_all_excluded_still_cannot_establish_compliance(self):
        for v in self.data['topics'].values():v.update(decision='excluded',reason='Synthetic exclusion test only')
        self.save();r=self.check()
        self.assertFalse(r['has_declared_gaps']);self.assertFalse(r['coverage_complete'])
        self.assertEqual(r['regulatory_compliance'],'not_established')

    def test_catalog_rule_drift_rejected(self):
        p=self.root/'hk/hvac-design-2026.11.08/pack.json';d=json.loads(p.read_text());d['rules'][0]['id']='changed'
        p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ProjectError,'rule list differs'):self.check()

    def test_scheduled_pack_is_not_executed_or_complete(self):
        pack_path=self.root/'hk/hvac-design-2026.11.08/pack.json'
        pack=json.loads(pack_path.read_text())
        pdf=self.root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
        pack['sources']['emsd_bec_2024']['sha256']=digest(pdf);pack_path.write_text(json.dumps(pack))
        shutil.copyfile(pack_path,self.root/'selected-pack.json')
        shutil.copyfile(ROOT/'examples/regulations-hk-hvac/project.json',self.root/'project.json')
        brief=self.root/'brief.md';brief.write_text('Check selected synthetic design conditions.')
        row=passages(brief)[0]
        plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},
                  tasks=[dict(id='hvac',kind='regulations',project='project.json',pack='selected-pack.json',sources='.')],
                  requirements=[dict(id='R1',passage=row['id'],quote=row['text'],task='hvac',acceptance='Check selected conditions')])
        path=self.root/'plan.json';path.write_text(json.dumps(plan))
        r=self.check(path);hvac=next(t for t in r['topics'] if t['id']=='hvac')
        self.assertEqual(hvac['modules'][0]['scheduled_tasks'],['hvac'])
        self.assertEqual(hvac['modules'][0]['execution_status'],'not_assessed')
        self.assertEqual(hvac['gaps'],['partial_rule_coverage'])


if __name__=='__main__':unittest.main()
