import tempfile
import unittest
from pathlib import Path
import ezdxf
from bsa.cad_block import select, structure, run
from bsa.engine import ProjectError


class BlockSelectionTests(unittest.TestCase):
    def fixture(self):
        doc = ezdxf.new('R2018'); doc.units = 1
        block = doc.blocks.new('tee')
        block.add_line((0, 0), (2.75, 0))
        insert = doc.modelspace().add_blockref('tee', (10, 0))
        insert.add_attrib('SIZE_MM', '40')
        basis = dict(source='synthetic identity control', drawing_sha256='a' * 64,
                     insert_handle=insert.dxf.handle, block_name='tee', insunits=1,
                     attributes={'SIZE_MM': '40'})
        return doc, block, insert, basis

    def test_explicit_instance_and_local_definition(self):
        doc, block, insert, basis = self.fixture()
        selected, attrs = select(doc, basis)
        self.assertIs(selected, block)
        self.assertEqual(attrs['SIZE_MM'], '40')
        self.assertEqual(selected[0].dxf.start.x, 0)
        self.assertEqual(insert.dxf.insert.x, 10)
        self.assertEqual(structure(block)['counts_by_type_layer'], [('LINE', '0', 1)])

    def test_wrong_identity_units_and_duplicate_tags_reject(self):
        doc, block, insert, basis = self.fixture()
        for update in ({'block_name': 'other'}, {'insert_handle': 'FFFF'},
                       {'insunits': 4}, {'attributes': {'SIZE_MM': '50'}}, {'attributes': {}}):
            with self.subTest(update=update), self.assertRaises(ProjectError):
                select(doc, dict(basis, **update))
        insert.add_attrib('SIZE_MM', '40')
        with self.assertRaises(ProjectError): select(doc, basis)

    def test_nested_and_xref_blocks_reject(self):
        doc, block, insert, basis = self.fixture()
        doc.blocks.new('child').add_circle((0, 0), 1)
        block.add_blockref('child', (0, 0))
        with self.assertRaises(ProjectError): select(doc, basis)
        doc, block, insert, basis = self.fixture()
        block.block.dxf.flags = 4
        with self.assertRaises(ProjectError): select(doc, basis)

    def test_stale_source_rejected_before_engine(self):
        import json
        parent = Path(__file__).resolve().parents[1] / 'runs'
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as folder:
            root = Path(folder); source = root / 'input.dwg'; source.write_bytes(b'synthetic')
            basis = root / 'selection.json'; basis.write_text(json.dumps(self.fixture()[3]))
            with self.assertRaisesRegex(ProjectError, 'source hash'):
                run(source, basis, root / 'out', root / 'no-engine.exe')
            self.assertFalse((root / 'out').exists())
