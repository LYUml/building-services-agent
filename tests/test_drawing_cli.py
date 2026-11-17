import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import main
from bsa import drawing_access,drawing_document

ROOT=Path(__file__).resolve().parents[1]

class DrawingCLITests(unittest.TestCase):
    def invoke(self,args):
        with patch('sys.argv',['bsa',*map(str,args)]),contextlib.redirect_stdout(io.StringIO()) as stream:
            code=main()
        return code,json.loads(stream.getvalue())

    def test_real_inspect_and_tamper_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);source=root/'document.json';source.write_bytes((ROOT/'examples/drawing-document.json').read_bytes())
            output=root/'drawing';drawing_document.run(source,output)
            code,value=self.invoke(['drawing','inspect',source,'--out',output])
            self.assertEqual(code,0);self.assertTrue(value['integrity_pass'])
            self.assertFalse(value['native_reopen_pass']);self.assertFalse(value['design_accepted'])
            with (output/'Drawing.dxf').open('a') as stream:stream.write('\nchanged\n')
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                self.invoke(['drawing','inspect',source,'--out',output])

    def test_missing_runtime_cannot_leave_partial_drawing(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);output=root/'must-not-exist'
            with self.assertRaisesRegex(ValueError,'existing AutoCAD'):
                drawing_access.run(ROOT/'examples/drawing-document.json',output,autocad=root/'missing.exe')
            self.assertFalse(output.exists())
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                self.invoke(['drawing','run',ROOT/'examples/drawing-document.json','--out',output,'--autocad',root/'missing.exe'])
            self.assertFalse(output.exists())

    def test_host_options_forward_to_the_shared_boundary(self):
        result=dict(integrity_pass=True,native_reopen_pass=True,visual_review='pending',design_accepted=False)
        with patch('bsa.drawing_access.run',return_value=result) as run:
            code,value=self.invoke(['drawing','run','recipe.json','--out','result','--autocad','host.exe','--graphviz','dot.exe'])
        self.assertEqual(code,0);self.assertFalse(value['design_accepted'])
        self.assertEqual(run.call_args.kwargs,dict(autocad=Path('host.exe'),graphviz=Path('dot.exe')))

if __name__=='__main__':unittest.main()
