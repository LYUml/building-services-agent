import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.network_binding import run as author
from bsa.ifc_water_rules import run

ROOT=Path(__file__).resolve().parents[1]


class IFCWaterRulesTests(unittest.TestCase):
    def test_saved_ifc_checks_and_tampering(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            root=Path(temp);example=ROOT/'examples/water-riser'
            author(example/'network.json',example/'model.json',example/'binding.json',root/'producer')
            original=json.loads((ROOT/'examples/regulations-hk-water/bases.json').read_text())
            basis=root/'basis.json';basis.write_text(json.dumps({'RISER':next(iter(original.values()))}))
            pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC UNIT TEST SOURCE')
            pack['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            pp=root/'pack.json';pp.write_text(json.dumps(pack))
            args=(root/'producer',example/'model.json',example/'binding.json',basis,pp,root)
            result=run(*args,root/'checked')
            self.assertTrue(result['saved_ifc_binding']['saved_geometry_reconciled'])
            self.assertFalse(result['design_accepted'])
            for name in ('bim/model.ifc','network-input.json'):
                p=root/'producer'/name;old=p.read_bytes();p.write_bytes(old+b'\n')
                with self.subTest(name=name),self.assertRaisesRegex(ProjectError,'artifact changed'):run(*args,root/'tampered')
                p.write_bytes(old)


if __name__=='__main__':unittest.main()
