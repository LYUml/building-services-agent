import json
from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.network_binding import run,reconcile

ROOT=Path(__file__).resolve().parents[1]


class SavedConnectionTests(unittest.TestCase):
    def test_missing_native_edges_rejected_with_geometry_unchanged(self):
        import ifcopenshell
        example=ROOT/'examples/water-riser'
        binding=json.loads((example/'binding.json').read_text());source=json.loads((example/'model.json').read_text())
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);run(example/'network.json',example/'model.json',example/'binding.json',root/'original')
            saved=root/'original/bim/model.ifc';network=root/'original/network-input.json'
            self.assertTrue(reconcile(saved,network,binding,source))
            native=ifcopenshell.open(str(saved));ids=[r.id() for r in native.by_type('IfcRelConnectsPorts')]
            self.assertGreaterEqual(len(ids),3)
            for relation in ids:
                model=ifcopenshell.open(str(saved));model.remove(model.by_id(relation))
                changed=root/'disconnected.ifc';model.write(str(changed))
                with self.subTest(relation=relation),self.assertRaisesRegex(ProjectError,'connection'):
                    reconcile(changed,network,binding,source)


if __name__=='__main__':unittest.main()
