import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.plumbing_pump_set import inputs, run
from bsa.workflow import execute, passages, verify

ROOT = Path(__file__).resolve().parents[1]


class PumpSetTests(unittest.TestCase):
    def test_separate_capacity_standby_failure_and_workflow_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for name in ('pump-set.json','network.json','curve.json','binding.json'):
                shutil.copyfile(ROOT/'examples/hk-plumbing-pumps'/name,root/name)
            pdf=root/'wsd-tr-2026-04.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            pack=json.loads((ROOT/'regulations/hk/plumbing-pumps-2026.11.09/pack.json').read_text())
            pack['sources']['wsd_tr_2026_04']['sha256']=digest(pdf);(root/'pack.json').write_text(json.dumps(pack))
            brief=root/'brief.md';brief.write_text('Check each synthetic pump alone and gate a subsequent recheck.')
            row=passages(brief)[0]
            common=dict(kind='plumbing_pump_set',project='pump-set.json',basis='binding.json',pack='pack.json',sources='.')
            tasks=[dict(common,id='capacity'),dict(common,id='after',requires_pass=['capacity']),
                   dict(id='standby',kind='pump_operating_point',project='network.json',curve='curve.json',
                        pump_role='standby',requires_pass=['after'])]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},tasks=tasks,
                      requirements=[dict(id=t['id'],passage=row['id'],quote=row['text'],task=t['id'],acceptance=row['text']) for t in tasks])
            file=root/'plan.json';file.write_text(json.dumps(plan))
            result=execute(file,root/'positive');self.assertTrue(result['execution_pass'],result['tasks'])
            self.assertTrue(verify(root/'positive')['integrity_pass'])
            curves=json.loads((root/'curve.json').read_text())
            for p in curves['points']:p['total_pressure_rise_pa']*=.1
            (root/'weak.json').write_text(json.dumps(curves))
            data=json.loads((root/'pump-set.json').read_text());data['pumps'][1]['curve']='weak.json'
            (root/'pump-set.json').write_text(json.dumps(data))
            plan['tasks'][-1]['curve']='weak.json';file.write_text(json.dumps(plan))
            result=execute(file,root/'negative')
            self.assertEqual(result['tasks']['capacity']['status'],'fail')
            self.assertEqual(result['tasks']['after']['status'],'pending')
            self.assertFalse((root/'negative/after').exists())
            self.assertEqual(result['tasks']['standby']['status'],'pending')
            self.assertFalse((root/'negative/standby').exists())
            report=json.loads((root/'negative/capacity/pump-set-checks.json').read_text())
            self.assertEqual([r['status'] for r in report['pump_checks']],['pass','fail'])
            self.assertFalse(report['individual_capacity_checks_pass'])
            self.assertFalse(verify(root/'positive')['integrity_pass'])
            self.assertIn(str(root/'weak.json'),result['inputs'])
            mismatch=json.loads((root/'network.json').read_text())
            mismatch['nodes'][-1]['required_total_pressure_pa']+=1
            (root/'other-network.json').write_text(json.dumps(mismatch))
            data['pumps'][1]['network']='other-network.json';(root/'pump-set.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError,'receiving-terminal boundary'):
                run(root/'pump-set.json',root/'binding.json',root/'pack.json',root,root/'mismatch')
            self.assertFalse((root/'mismatch').exists())
            data['pumps'][1]['id']=data['pumps'][0]['id'];(root/'pump-set.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError,'distinct'):inputs(root/'pump-set.json')
