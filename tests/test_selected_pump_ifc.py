import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa.bim import run as author
from bsa.water_binding import run as bind
from bsa.circulation_pump_design import run as screen
from bsa.selected_pump_ifc import run
from bsa.cli import digest
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/circulation-ifc'


class SelectedPumpIFCTests(unittest.TestCase):
    def test_source_preservation_native_rebind_and_wrong_screen(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);author(EX/'model.json',root/'model');bind(EX/'project.json',root/'model/model.ifc',EX/'binding.json',root/'bound')
            original=root/'bound/model.ifc';before=digest(original)
            catalogue=root/'catalogue.json';c=json.loads((ROOT/'examples/hvac-circulation/pump-catalogue.json').read_text());c['candidates']=c['candidates'][-1:]
            c['candidates'][0]['head_curve']=[[0,7],[.005,.1]];catalogue.write_text(json.dumps(c))
            pdf=root/'emsd-bec-2024.pdf';pdf.write_bytes(b'SYNTHETIC TEST SOURCE')
            p=json.loads((ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json').read_text());p['sources']['emsd_bec_2024']['sha256']=digest(pdf);pack=root/'pack.json';pack.write_text(json.dumps(p))
            screen(root/'bound/network-input.json',catalogue,ROOT/'examples/hvac-circulation/thermal-duty.json',EX/'regulatory-bases.json',pack,root,root/'screen')
            result=run(root/'bound',root/'screen',EX/'project.json',EX/'binding.json',catalogue,root/'selected')
            self.assertTrue(result['calculated_checks_pass']);self.assertEqual(digest(original),before)
            a=ifcopenshell.open(str(original));b=ifcopenshell.open(str(root/'selected/selected-model.ifc'))
            for cls in ('IfcDistributionElement','IfcDistributionPort'):
                self.assertEqual({x.GlobalId for x in a.by_type(cls)},{x.GlobalId for x in b.by_type(cls)})
            template=json.loads((root/'selected/selected-template.json').read_text());self.assertEqual(template['pumps'][0]['head_curve'],[[0,7],[.005,.1]])
            wrong=root/'wrong-catalogue.json';wrong.write_text(json.dumps(c))
            with self.assertRaisesRegex(ProjectError,'source identity differs'):
                run(root/'bound',root/'screen',EX/'project.json',EX/'binding.json',wrong,root/'wrong')
            self.assertFalse((root/'wrong').exists())
