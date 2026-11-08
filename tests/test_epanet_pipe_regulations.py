import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.epanet_pipe_regulations import run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/hvac-circulation'


class EPANETRuleTests(unittest.TestCase):
    def test_actual_small_failure_large_pass_and_density(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
            pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            packfile=root/'pack.json';packfile.write_text(json.dumps(pack))
            for suffix,expected in [('',False),('-65mm',True)]:
                result=run(EX/f'project{suffix}.json',EX/f'regulatory-bases{suffix}.json',packfile,root,root/('run'+suffix))
                self.assertTrue(result['hydraulic_checks_pass'])
                self.assertEqual(result['supported_checks_pass'],expected)
                bound=json.loads((root/('run'+suffix)/'bound-pipe-projects.json').read_text())
                self.assertAlmostEqual(bound['REFERENCE']['water_pipe']['linear_friction']['value'],0,delta=1e-8)
                hydraulic=json.loads((root/('run'+suffix)/'network/water.json').read_text())
                row=next(r for r in hydraulic['pipes'] if r['id']=='OUTBOUND')
                pipe=next(r for r in hydraulic['source_data']['pipes'] if r['id']=='OUTBOUND')
                expected_loss=row['energy']['darcy_factor']*1000*row['velocity_m_s']**2/(2*pipe['diameter_m'])
                self.assertAlmostEqual(bound['OUTBOUND']['water_pipe']['linear_friction']['value'],expected_loss)
            basis=json.loads((EX/'regulatory-bases.json').read_text());basis['density']['unit']='kg'
            bad=root/'bad.json';bad.write_text(json.dumps(basis))
            with self.assertRaises(ProjectError):run(EX/'project.json',bad,packfile,root,root/'bad-run')


if __name__=='__main__':unittest.main()
