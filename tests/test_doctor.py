import importlib.metadata as metadata
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa import doctor,workspace,drawing_access

class DoctorTests(unittest.TestCase):
    def test_missing_pin_and_unknown_extra_are_explicit(self):
        def version(name):
            if name=='pypdf':raise metadata.PackageNotFoundError(name)
            return '1.4.5'
        with patch('bsa.doctor.metadata.version',side_effect=version):
            result=doctor.check(extras=['drawing'])
        self.assertEqual(result['status'],'needs_setup')
        self.assertIsNone(next(p for p in result['packages'] if p['package']=='pypdf')['installed'])
        self.assertFalse(result['design_accepted'])
        with self.assertRaisesRegex(ValueError,'Unknown extras'):doctor.check(extras=['guess'])

    def test_existing_executable_is_presence_only(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            exe=Path(folder)/'fixture.exe';exe.write_text('Not an executable')
            result=doctor.check(autocad=exe)
            self.assertTrue(result['autocad']['is_file']);self.assertFalse(result['autocad']['execution_verified'])
            self.assertEqual(doctor.check(autocad=Path(folder)/'missing')['status'],'needs_setup')

    def test_missing_native_dependency_rejects_before_output(self):
        with tempfile.TemporaryDirectory(dir=workspace.ROOT/'runs') as folder:
            root=Path(folder);exe=root/'fixture.exe';exe.touch();out=root/'new'
            with patch('bsa.drawing_access.metadata.version',side_effect=metadata.PackageNotFoundError('pypdf')):
                with self.assertRaisesRegex(ValueError,'drawing extra'):
                    drawing_access.run(workspace.ROOT/'examples/drawing-document.json',out,autocad=exe)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
