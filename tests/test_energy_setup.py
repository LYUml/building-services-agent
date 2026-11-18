from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from scripts.setup_energy import verify_installation


class EnergySetupTests(unittest.TestCase):
    def test_interrupted_extraction_can_be_retried(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "engine.zip"
            target = root / "install"
            with ZipFile(archive, "w") as package:
                package.writestr("engine.dat", b"verified")

            def interrupted_extract(package, path):
                path.mkdir()
                (path / "engine.dat").write_bytes(b"partial")
                raise OSError("extraction interrupted")

            with patch.object(ZipFile, "extractall", interrupted_extract):
                with self.assertRaisesRegex(OSError, "extraction interrupted"):
                    verify_installation(archive, target)
            self.assertFalse(target.exists())

            verify_installation(archive, target)
            self.assertEqual((target / "engine.dat").read_bytes(), b"verified")
            (target / "engine.dat").write_bytes(b"modified")
            with self.assertRaisesRegex(RuntimeError, "engine.dat"):
                verify_installation(archive, target)
            self.assertEqual((target / "engine.dat").read_bytes(), b"modified")
