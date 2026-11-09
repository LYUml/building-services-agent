import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.circulation_pump_design import candidates,run
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/hvac-circulation'


class CirculationPumpDesignTests(unittest.TestCase):
    def test_candidate_isolation_and_contract(self):
        p=json.loads((EX/'project-65mm.json').read_text());original=copy.deepcopy(p)
        c=json.loads((EX/'pump-catalogue.json').read_text());result=candidates(p,c)
        self.assertEqual(p,original)
        for _,network in result:
            self.assertEqual(network['pipes'],p['pipes']);self.assertEqual(network['junctions'],p['junctions'])
        c['candidates'][1]['id']=c['candidates'][0]['id']
        with self.assertRaises(ProjectError):candidates(p,c)

    def test_no_feasible_pump_preserves_rejections(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text());pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            packfile=root/'pack.json';packfile.write_text(json.dumps(pack))
            c=json.loads((EX/'pump-catalogue.json').read_text());c['candidates']=c['candidates'][:2]
            catalogue=root/'catalogue.json';catalogue.write_text(json.dumps(c))
            result=run(EX/'project-65mm.json',catalogue,EX/'thermal-duty.json',EX/'regulatory-bases-65mm.json',packfile,root,root/'run')
            self.assertFalse(result['feasible_candidate_found']);self.assertIsNone(result['selected'])
            self.assertFalse((root/'run/selected').exists())
            self.assertEqual(len(result['candidates']),2)
            self.assertTrue(result['candidates'][0]['hydraulic_checks_pass'])
            self.assertFalse(result['candidates'][0]['thermal_checks_pass'])
            self.assertFalse(result['candidates'][1]['hydraulic_checks_pass'])
            self.assertTrue(result['baseline']['pass_checks'])
