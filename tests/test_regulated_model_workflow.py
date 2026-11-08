import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.workflow import execute,passages,validate_plan

ROOT=Path(__file__).resolve().parents[1]


class RegulatedWorkflowTests(unittest.TestCase):
    def test_preflight_tracks_sources_and_failed_design_blocks_drawing(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder)
            for name in ('network','model','binding','catalogue','geometry','drawing-settings'):
                shutil.copyfile(ROOT/('examples/water-riser/'+name+'.json'),root/(name+'.json'))
            for name in ('bases','classifications'):
                shutil.copyfile(ROOT/('examples/regulations-hk-water/riser-'+name+'.json'),root/(name+'.json'))
            pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            (root/'pack.json').write_text(json.dumps(pack))
            brief=root/'brief.md';brief.write_text('Select and author a regulated model.\n\nDraw the selected model.')
            rows=passages(brief)
            tasks=[dict(id='design',kind='regulated_water_model',project='network.json',model='model.json',binding='binding.json',catalogue='catalogue.json',geometry='geometry.json',basis='bases.json',classifications='classifications.json',pack='pack.json',sources='.'),dict(id='drawing',kind='ifc_drawing',depends_on='design',settings='drawing-settings.json')]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,requirements=[dict(id=str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance=r['text']) for i,(r,t) in enumerate(zip(rows,tasks))])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            _,inputs=validate_plan(path)
            for name in ('network','model','binding','catalogue','geometry','bases','classifications','pack'):
                self.assertIn(root/(name+'.json'),inputs)
            self.assertIn(pdf,inputs)
            with patch('bsa.regulated_water_model.run',return_value={'calculated_checks_pass':False,'scope':'Synthetic failed selection control'}),patch('bsa.ifc_drawing.run') as drawing:
                result=execute(path,root/'run')
            self.assertEqual(result['tasks']['design']['status'],'fail')
            self.assertEqual(result['tasks']['drawing']['status'],'pending');drawing.assert_not_called()


if __name__=='__main__':unittest.main()
