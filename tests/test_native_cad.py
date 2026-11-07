import os
from pathlib import Path
import tempfile
import unittest
from bsa.cli import run
from bsa.native_cad import convert, plot, DEFAULT_EXE
from bsa.engine import ProjectError

EXAMPLE=Path(__file__).resolve().parents[1]/"examples/office-electrical/project.json"

class NativeCADTests(unittest.TestCase):
    def test_missing_executable_does_not_create_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/"native"
            with self.assertRaises(ProjectError):
                convert(EXAMPLE,out,Path(folder)/"missing.exe")
            self.assertFalse(out.exists())

    @unittest.skipUnless(os.environ.get("BSA_TEST_AUTOCAD")=="1" and DEFAULT_EXE.is_file(),
                         "requires explicit local AutoCAD integration test")
    def test_real_native_save_reopen_and_plot(self):
        # All test outputs are created inside this repository's ignored runs directory.
        root=Path(__file__).resolve().parents[1]/"runs"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            run(EXAMPLE,Path(folder)/"data")
            source=Path(folder)/"data/devices.dxf"
            out=Path(folder)/"native"
            result=convert(source,out)
            self.assertTrue(result["native_reopen_pass"])
            plotted=plot(out/"devices.dwg",source,out/"devices.pdf")
            self.assertEqual(plotted["visual_review"],"pending")
            self.assertTrue((out/"devices.pdf").read_bytes().startswith(b"%PDF-"))

if __name__=="__main__":unittest.main()
