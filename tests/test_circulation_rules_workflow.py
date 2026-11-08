import json
import shutil
from tests.test_circulation_workflow import CirculationWorkflowTests, ROOT
from bsa.cli import digest
from bsa.workflow import execute, verify


class CombinedWorkflowTests(CirculationWorkflowTests):
    def setUp(self):
        super().setUp()
        ex=ROOT/'examples/hvac-circulation'
        shutil.copyfile(ex/'project-65mm.json',self.root/'project.json')
        shutil.copyfile(ex/'regulatory-bases-65mm.json',self.root/'basis.json')
        pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
        pdf=self.root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
        pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
        (self.root/'pack.json').write_text(json.dumps(pack))
        self.plan['tasks'].insert(1,dict(id='rules',kind='epanet_pipe_regulations',project='project.json',basis='basis.json',pack='pack.json',sources='.',requires_pass=['duty']))
        self.plan['tasks'][-1]['requires_pass']=['rules']
        req=dict(self.plan['requirements'][0]);req.update(id='rules',task='rules')
        self.plan['requirements'].append(req)

    def test_regulatory_review_blocks_downstream(self):
        shutil.copyfile(ROOT/'examples/hvac-circulation/project.json',self.root/'project.json')
        shutil.copyfile(ROOT/'examples/hvac-circulation/regulatory-bases.json',self.root/'basis.json')
        self.save();result=execute(self.path,self.root/'run')
        self.assertEqual(result['tasks']['duty']['status'],'pass')
        self.assertEqual(result['tasks']['rules']['status'],'pending')
        self.assertEqual(result['tasks']['water']['status'],'pending')
        self.assertFalse((self.root/'run/water').exists())

    def test_official_bytes_recorded(self):
        self.save();result=execute(self.path,self.root/'run')
        self.assertEqual(result['tasks']['rules']['status'],'pass')
        self.assertTrue(verify(self.root/'run')['integrity_pass'])
        (self.root/'emsd-bec-2024.pdf').write_bytes(b'changed')
        self.assertFalse(verify(self.root/'run')['integrity_pass'])
