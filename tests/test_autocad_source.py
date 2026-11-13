import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa import autocad_source as adapter

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless((adapter.UPSTREAM/'.git').exists() and importlib.util.find_spec('ezdxf'),'requires pinned upstream checkout and existing DXF runtime')
class AutoCADSourceTests(unittest.TestCase):
    def setUp(self):
        import ezdxf
        temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.env=patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(self.root)});self.env.start();self.addCleanup(self.env.stop)
        self.source=self.root/'source.dxf';self.out=self.root/'inspection'
        doc=ezdxf.new('R2018');doc.units=6;doc.layers.new('SOURCE')
        block=doc.blocks.new('DECLARED_BLOCK');block.add_line((0,0),(1,0))
        doc.modelspace().add_line((0,0),(10,0),dxfattribs={'layer':'SOURCE'})
        doc.modelspace().add_blockref('DECLARED_BLOCK',(3,2))
        doc.layouts.new('Declared Sheet');doc.saveas(self.source)

    def test_real_upstream_reads_source_and_all_layouts(self):
        before=self.source.read_bytes();result=adapter.run(self.source,self.out)
        self.assertEqual(result['status'],'inspected');checked=adapter.verify(self.out)
        self.assertEqual(checked['entities'],2);self.assertEqual(checked['layouts'],3)
        self.assertEqual(checked['insunits'],6);self.assertFalse(checked['design_accepted'])
        self.assertEqual(self.source.read_bytes(),before)
        raw=json.loads((self.out/'upstream/inventory.json').read_text())
        self.assertIn('Declared Sheet',raw['layouts']['layouts'])
        self.assertTrue(any(r['name']=='DECLARED_BLOCK' for r in raw['blocks']))

    def test_shared_cli_executes_and_verifies_actual_upstream(self):
        import contextlib, io
        from bsa.cli import main
        before=self.source.read_bytes()
        for args in (['autocad-source','run','--source',self.source,'--out',self.out], ['autocad-source','verify',self.out]):
            with patch('sys.argv',['bsa',*map(str,args)]),contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(),0)
            result=json.loads(output.getvalue());self.assertFalse(result['design_accepted'])
        self.assertTrue(result['integrity_pass']);self.assertEqual(self.source.read_bytes(),before)
        self.source.write_bytes(self.source.read_bytes()+b'changed')
        with patch('sys.argv',['bsa','autocad-source','verify',str(self.out)]),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failed:main()
        self.assertEqual(failed.exception.code,2)

    def test_changed_source_cannot_keep_inspection_current(self):
        adapter.run(self.source,self.out);self.source.write_bytes(self.source.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'Source, engine'):adapter.verify(self.out)

    def test_changed_upstream_result_cannot_pass(self):
        adapter.run(self.source,self.out);path=self.out/'upstream/inventory.json'
        data=json.loads(path.read_text());data['entities']=[];path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'artifact changed'):adapter.verify(self.out)

    def test_workspace_escape_and_existing_output_reject(self):
        with self.assertRaises(ValueError):adapter.run(self.source,ROOT/'runs/outside-selected-project')
        self.out.mkdir()
        with self.assertRaises(ValueError):adapter.run(self.source,self.out)

if __name__=='__main__':unittest.main()
