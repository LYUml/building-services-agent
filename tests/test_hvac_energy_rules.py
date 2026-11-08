import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.hvac_energy_rules import run
from bsa.workflow import execute,passages,validate_plan,verify

ROOT=Path(__file__).resolve().parents[1]
EXE=ROOT/'tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe'


class HVACWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copyfile(ROOT/'examples/regulations-hk-hvac/native-energy-project.json',self.root/'project.json')
        shutil.copyfile(ROOT/'examples/regulations-hk-hvac/zone-bases.json',self.root/'basis.json')
        pack=json.loads((ROOT/'regulations/hk/hvac-design-2026.11.08/pack.json').read_text())
        pdf=self.root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE ONLY')
        pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
        (self.root/'pack.json').write_text(json.dumps(pack))
        brief=self.root/'brief.md';brief.write_text('Run energy.\n\nCheck design conditions.\n\nReview remaining requirements.')
        rows=passages(brief)
        tasks=[dict(id='energy',kind='energy',project='project.json'),dict(id='hk',kind='hvac_regulations',depends_on='energy',basis='basis.json',pack='pack.json',sources='.'),dict(id='review',kind='manual',requires_pass=['hk'])]
        self.plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,requirements=[dict(id=str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
        self.path=self.root/'plan.json';self.save()

    def save(self):self.path.write_text(json.dumps(self.plan))

    def test_missing_engine_blocks_checks_and_downstream(self):
        result=execute(self.path,self.root/'run')
        self.assertEqual(result['tasks']['hk']['status'],'pending')
        self.assertIn('upstream energy',result['tasks']['hk']['scope'])
        self.assertIn('required checks unresolved',result['tasks']['review']['scope'])
        self.assertFalse((self.root/'run/hk').exists())
        self.assertTrue(verify(self.root/'run')['integrity_pass'])

    def test_invalid_producer_and_replacement_inputs_rejected(self):
        for change in ({'depends_on':'review'},{'depends_on':'missing'},{'idf':'other.idf'},{'variant':'baseline'}):
            original=dict(self.plan['tasks'][1]);self.plan['tasks'][1].update(change);self.save()
            with self.subTest(change=change),self.assertRaises(ProjectError):validate_plan(self.path)
            self.plan['tasks'][1]=original

    @unittest.skipUnless(EXE.is_file(),'requires actual EnergyPlus 25.2')
    def test_actual_variants_and_postrun_native_tampering(self):
        result=execute(self.path,self.root/'run',energyplus=EXE)
        self.assertEqual(result['tasks']['hk']['status'],'pass',result['tasks']['hk']['scope'])
        self.assertFalse(result['design_accepted'])
        check=json.loads((self.root/'run/hk/energy-regulation-checks.json').read_text())
        self.assertEqual(set(check['variants']),{'baseline','variant'})
        self.assertTrue(verify(self.root/'run')['integrity_pass'])
        for name in ('baseline','variant'):
            model=self.root/'run/energy'/name/'model.idf';original=model.read_bytes()
            model.write_bytes(original+b'\n! changed after execution\n')
            with self.subTest(name=name),self.assertRaisesRegex(ProjectError,'artifact differs'):
                run(self.root/'run/energy',self.root/'basis.json',self.root/'pack.json',self.root,self.root/('tampered-'+name))
            model.write_bytes(original)
        sql=self.root/'run/energy/variant/eplusout.sql';sql.write_bytes(b'not executed SQL')
        with self.assertRaisesRegex(ProjectError,'artifact differs'):
            run(self.root/'run/energy',self.root/'basis.json',self.root/'pack.json',self.root,self.root/'tampered-sql')


if __name__=='__main__':unittest.main()
