import json
from pathlib import Path
import tempfile
import unittest
from bsa.bim import run as author
from bsa.water_binding import run as bind
from bsa.ifc_circulation_checks import run,verify_producer
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/circulation-ifc'


class BoundCirculationChecks(unittest.TestCase):
    def test_native_checks_and_changed_derived_geometry(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);author(EX/'model.json',root/'model')
            bind(EX/'project.json',root/'model/model.ifc',EX/'binding.json',root/'bound')
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            p=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text());p['sources']['emsd_bec_2024']['sha256']=digest(pdf)
            pack=root/'pack.json';pack.write_text(json.dumps(p))
            r=run(root/'bound',EX/'project.json',EX/'binding.json',ROOT/'examples/hvac-circulation/thermal-duty.json',EX/'regulatory-bases.json',pack,root,root/'checks')
            self.assertEqual(r['status'],'pass');self.assertFalse(r['design_accepted'])
            network=root/'bound/network-input.json';data=json.loads(network.read_text());data['pipes'][1]['length_m']+=1;network.write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError,'artifact changed'):
                verify_producer(root/'bound',EX/'project.json',EX/'binding.json')
            report=root/'bound/water-binding.json';data=json.loads(report.read_text());data['artifacts']['network-input.json']=digest(network);report.write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError,'saved IFC differs'):
                verify_producer(root/'bound',EX/'project.json',EX/'binding.json')
