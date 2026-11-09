import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,verify,passages,validate_plan
from bsa.circulation_pump_design import selected_input
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class PumpScreenWorkflowTests(unittest.TestCase):
    def test_selection_and_no_feasible_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);ex=ROOT/'examples/hvac-circulation'
            for name in ('project-65mm.json','pump-catalogue.json','thermal-duty.json','regulatory-bases-65mm.json'):shutil.copyfile(ex/name,root/name)
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text());pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            (root/'pack.json').write_text(json.dumps(pack))
            brief=root/'brief.md';brief.write_text('Screen sourced candidate pumps against duty and pipe rules.\n\nReview the selected pump and complete engineering acceptance.')
            rows=passages(brief)
            tasks=[dict(id='screen',kind='circulation_pump_design',project='project-65mm.json',catalogue='pump-catalogue.json',thermal_basis='thermal-duty.json',rule_basis='regulatory-bases-65mm.json',pack='pack.json',sources='.'),dict(id='review',kind='water_network',depends_on='screen')]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,requirements=[dict(id=str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
            file=root/'plan.json';file.write_text(json.dumps(plan))
            plan['tasks'][1]['project']='project-65mm.json';file.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ProjectError,'no replacement project'):validate_plan(file)
            del plan['tasks'][1]['project'];file.write_text(json.dumps(plan))
            result=execute(file,root/'pass');self.assertEqual(result['tasks']['screen']['status'],'pass')
            self.assertTrue(verify(root/'pass')['integrity_pass'])
            self.assertEqual(result['tasks']['review']['status'],'pass')
            selected=root/'pass/screen/selected/project.json'
            native=json.loads((root/'pass/review/water.json').read_text())
            self.assertEqual(native['input_sha256'],digest(selected))
            original=selected.read_bytes();selected.write_text('{}')
            with self.assertRaisesRegex(ProjectError,'artifact changed'):
                selected_input(root/'pass/screen',root/'project-65mm.json',root/'pump-catalogue.json')
            selected.write_bytes(original)
            c=json.loads((root/'pump-catalogue.json').read_text());c['candidates']=c['candidates'][:2];(root/'pump-catalogue.json').write_text(json.dumps(c))
            self.assertFalse(verify(root/'pass')['integrity_pass'])
            result=execute(file,root/'fail');self.assertEqual(result['tasks']['screen']['status'],'fail')
            self.assertEqual(result['tasks']['review']['status'],'pending')
            self.assertFalse((root/'fail/review').exists())
            self.assertFalse((root/'fail/screen/selected').exists())
