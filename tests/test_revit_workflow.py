"""Workflow controls with deliberately non-RVT bytes; no native model claim."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from bsa.workflow import execute, verify
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]


class RevitWorkflowTests(unittest.TestCase):
    def fixture(self, root, physical=False):
        brief=root/'brief.md'
        statements=['Check the saved connector inventory.', 'Review the complete system before delivery.']
        brief.write_text('\n\n'.join(statements),encoding='utf-8')
        model=root/'synthetic-model-bytes.rvt'
        model.write_bytes(b'NOT A REVIT MODEL: workflow hash fixture only')
        inventory=dict(document_path=str(model),saved_rvt_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
                       units='metres',fittings=[],pipes=[dict(unique_id='p',connectors=[dict(id=1,
                       origin_m=[0,0,0],domain='DomainPiping',connector_type='End',
                       physically_connected=physical,references=[])])])
        (root/'inventory.json').write_text(json.dumps(inventory))
        plan=dict(version=1,brief='brief.md',brief_sha256=hashlib.sha256(brief.read_bytes()).hexdigest(),
                  passage_dispositions={'P001':'requirement','P002':'requirement'},
                  tasks=[dict(id='check',kind='revit_inventory_check',inventory='inventory.json',
                              model=model.name,tolerance_m=0.0001),
                         dict(id='delivery',kind='manual',requires_pass=['check'],description='Full system review')],
                  requirements=[dict(id=f'R{i+1}',passage=f'P00{i+1}',quote=text,
                                     task=['check','delivery'][i],acceptance=text) for i,text in enumerate(statements)])
        path=root/'plan.json';path.write_text(json.dumps(plan))
        return path,model

    def test_pending_diagnosis_blocks_delivery_and_retains_hashes(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);plan,model=self.fixture(root)
            result=execute(plan,root/'out')
            self.assertEqual(result['tasks']['check']['status'],'pending')
            self.assertEqual(result['tasks']['delivery']['status'],'pending')
            self.assertFalse(result['execution_pass'])
            self.assertTrue(verify(root/'out')['integrity_pass'])
            rows=diagnose(plan,root/'out')['tasks']
            self.assertEqual(rows[1]['blocked_by'],['check'])
            model.write_bytes(b'changed fixture')
            self.assertFalse(verify(root/'out')['integrity_pass'])

    def test_inconsistent_observation_fails_upstream(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);plan,_=self.fixture(root,physical=True)
            result=execute(plan,root/'out')
            self.assertEqual(result['tasks']['check']['status'],'fail')
            self.assertFalse((root/'out/delivery').exists())

    def test_stale_inventory_is_rejected_before_diagnosis_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);plan,model=self.fixture(root)
            model.write_bytes(b'changed before run')
            result=execute(plan,root/'out')
            self.assertEqual(result['tasks']['check']['status'],'fail')
            self.assertFalse((root/'out/check/diagnosis.json').exists())


if __name__=='__main__':unittest.main()
