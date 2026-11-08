import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.regulated_water_model import run

ROOT=Path(__file__).resolve().parents[1]


class RegulatedModelTests(unittest.TestCase):
    def test_selected_ifc_and_no_feasible_candidate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            root=Path(temp);example=ROOT/'examples/water-riser';basis=ROOT/'examples/regulations-hk-water'
            pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC UNIT TEST SOURCE')
            pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            pp=root/'pack.json';pp.write_text(json.dumps(pack))
            def execute(network,out):return run(network,*(example/(name+'.json') for name in ('model','binding','catalogue','geometry')),basis/'riser-bases.json',basis/'riser-classifications.json',pp,root,out)
            result=execute(example/'network.json',root/'positive')
            self.assertEqual(result['selected']['choices'],{'RISER':'D40'})
            self.assertTrue(result['saved_ifc_checks_pass']);self.assertTrue(result['stable_object_port_ids_match'])
            self.assertTrue(result['calculated_checks_pass']);self.assertFalse(result['design_accepted'])
            self.assertTrue((root/'positive/selected-coordination/bim/model.ifc').is_file())
            p=json.loads((example/'network.json').read_text());p['supply']['total_pressure_pa']=0
            np=root/'low.json';np.write_text(json.dumps(p))
            negative=execute(np,root/'negative')
            self.assertIsNone(negative['selected']);self.assertFalse(negative['calculated_checks_pass'])
            self.assertFalse((root/'negative/selected-model.json').exists())


if __name__=='__main__':unittest.main()
