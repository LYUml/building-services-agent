import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.water_pipe_design import run

ROOT=Path(__file__).resolve().parents[1]


class WaterPipeDesignTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.example=ROOT/'examples/regulations-hk-water'
        pack=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text())
        self.pdf=self.root/'emsd-bec-2024.pdf';self.pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
        pack['sources']['emsd_bec_2024']['sha256']=digest(self.pdf)
        self.pack=self.root/'pack.json';self.pack.write_text(json.dumps(pack))
        self.classes=self.root/'classes.json';self.classes.write_bytes((self.example/'classifications.json').read_bytes())

    def execute(self):return run(self.example/'network.json',self.example/'catalogue.json',self.example/'bases.json',self.classes,self.pack,self.root,self.root/'out')

    def test_regulation_rejects_cheaper_hydraulically_feasible_candidate(self):
        r=self.execute()
        self.assertEqual(r['candidate_count'],3)
        middle=r['candidates'][1]
        self.assertTrue(middle['hydraulic_checks_pass']);self.assertFalse(middle['supported_checks_pass'])
        self.assertEqual(r['selected']['choices'],{'PIPE1':'D40'})
        self.assertTrue(r['selected_rerun_pass']);self.assertFalse(r['design_accepted'])

    def test_unavailable_source_selects_nothing(self):
        self.pdf.unlink();r=self.execute()
        self.assertIsNone(r['selected']);self.assertFalse(r['selected_rerun_pass'])
        self.assertEqual(len(r['candidates']),3)

    def test_classification_cannot_be_silently_inferred(self):
        self.classes.write_text('{}')
        with self.assertRaisesRegex(ProjectError,'classification'):self.execute()


if __name__=='__main__':unittest.main()
