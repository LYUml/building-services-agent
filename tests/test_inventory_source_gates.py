import tempfile
from pathlib import Path
import unittest
from bsa.engine import ProjectError
from bsa.workflow import inventory_source_bindings

ROOT=Path(__file__).resolve().parents[1]


class InventorySourceGateTests(unittest.TestCase):
    def test_transitive_explicit_byte_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            (root/'a.ifc').write_text('SYNTHETIC IDENTITY TEST BYTES')
            (root/'copy.ifc').write_bytes((root/'a.ifc').read_bytes())
            (root/'b.ifc').write_text('DIFFERENT SYNTHETIC BYTES')
            tasks=[dict(id='inventory',kind='ifc_query',ifc='a.ifc'),
                   dict(id='review',kind='manual',requires_pass=['inventory']),
                   dict(id='drawing',kind='ifc_drawing',ifc='copy.ifc',requires_pass=['review'])]
            rows=inventory_source_bindings(tasks,root)
            self.assertEqual(rows[0]['consumer'],'drawing')
            self.assertIn('sha256',rows[0]['model_identity'])
            for kind in ('ifc_query','ids_check','ifc_clash','ifc_drawing','ifc_route_drawing','ifc_views','water_coordination','annual_energy_ifc'):
                tasks[-1].update(kind=kind,ifc='b.ifc')
                with self.assertRaisesRegex(ProjectError,'different model'):
                    inventory_source_bindings(tasks,root)

    def test_inherited_producer_must_match(self):
        tasks=[dict(id='a',kind='bim'),dict(id='b',kind='bim'),
               dict(id='inventory',kind='ifc_query',depends_on='a'),
               dict(id='query',kind='ifc_query',depends_on='a',requires_pass=['inventory'])]
        self.assertEqual(inventory_source_bindings(tasks,ROOT)[0]['model_identity'],{'producer':'a'})
        tasks[-1]['depends_on']='b'
        with self.assertRaisesRegex(ProjectError,'different model'):inventory_source_bindings(tasks,ROOT)
