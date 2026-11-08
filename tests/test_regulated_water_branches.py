import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.water_pipe_design import run

ROOT=Path(__file__).resolve().parents[1]


class BranchSelectionTests(unittest.TestCase):
    def test_independent_flow_area_bound_and_input_order_invariance(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);example=ROOT/'examples/regulations-hk-water-branches'
            pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC UNIT TEST SOURCE')
            pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            pp=root/'pack.json';pp.write_text(json.dumps(pack))
            cat=json.loads((example/'catalogue.json').read_text())
            flows={'TRUNK':.0004+.0008,'BRANCH-A':.0004,'BRANCH-B':.0008}
            limit=pack['rules'][0]['limits']['small_velocity_max_m_s']
            # Independent v=Q/A lower bound, with strictly increasing material scores.
            expected={id:min((o for o in cat['options'] if o['diameter_m']>=math.sqrt(4*q/(math.pi*limit))),key=lambda o:o['material_score_per_m'])['id'] for id,q in flows.items()}
            def execute(project,out):return run(project,example/'catalogue.json',example/'bases.json',example/'classifications.json',pp,root,out)
            result=execute(example/'network.json',root/'first')
            self.assertEqual(result['candidate_count'],27)
            self.assertEqual(result['selected']['choices'],expected)
            self.assertEqual(result['selected']['material_score'],758)
            actual=json.loads((root/'first/selected-rerun/network/network.json').read_text())
            for s in actual['segments']:self.assertAlmostEqual(s['flow_m3_s'],flows[s['id']])
            self.assertAlmostEqual(actual['supply_flow_m3_s'],.0012)
            original=json.loads((example/'network.json').read_text())
            original['nodes'].reverse();original['segments'].reverse()
            changed=root/'reordered.json';changed.write_text(json.dumps(original))
            reordered=execute(changed,root/'second')
            self.assertEqual(reordered['selected']['choices'],expected)
            self.assertEqual(reordered['selected']['material_score'],758)
            self.assertFalse(reordered['design_accepted'])


if __name__=='__main__':unittest.main()
