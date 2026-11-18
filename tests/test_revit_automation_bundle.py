import hashlib
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree
from zipfile import ZipFile

from scripts.prepare_revit_automation_bundle import prepare


class RevitAutomationBundleTests(unittest.TestCase):
    def test_write_bundle_has_distinct_entrypoint_and_transfers(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            directory = Path(temporary)
            assembly = directory / 'Bsa.Revit.Automation.dll'
            assembly.write_bytes(b'synthetic assembly')
            model = directory / 'fixture.rvt'
            model.write_bytes(b'synthetic RVT')
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            request = directory / 'draft.json'
            request.write_text(json.dumps({'SavedRvtSha256': digest}), encoding='utf-8')
            args = dict(engine='Autodesk.Revit+2027', bundle_id='example.CreatePipe+review',
                        operation='create-pipe', model=model, pipe_request=request)
            archive = prepare(assembly, directory / 'published', **args)
            with ZipFile(archive) as bundle:
                manifest, = [name for name in bundle.namelist() if name.endswith('.addin')]
                addin = ElementTree.fromstring(bundle.read(manifest)).find('AddIn')
                self.assertEqual(addin.findtext('FullClassName'), 'Bsa.Revit.AutomationCreatePipe')
            activity = json.loads(archive.with_name('activity.json').read_bytes())
            self.assertEqual(activity['id'], 'BsaRevitCreatePipe')
            self.assertEqual({row['localName']: row['verb'] for row in activity['parameters'].values()}, {
                'input.rvt': 'get', 'pipe-request.json': 'get', 'authored.rvt': 'put', 'creation.json': 'put',
            })
            self.assertEqual(archive.with_name('pipe-request.json').read_bytes(), request.read_bytes())
            model.write_bytes(b'different RVT')
            rejected = directory / 'rejected'
            with self.assertRaisesRegex(ValueError, 'does not match'):
                prepare(assembly, rejected, **args)
            self.assertFalse(rejected.exists())

    def test_repeatable_bundle_and_hash_bound_request(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            directory = Path(temporary)
            assembly = directory / 'Bsa.Revit.Automation.dll'
            assembly.write_bytes(b'synthetic assembly bytes for archive layout test')
            model = directory / 'fixture.rvt'
            model.write_bytes(b'synthetic model bytes for request binding test')
            arguments = dict(engine='Autodesk.Revit+2027', bundle_id='example.Inventory+review', model=model)
            first = prepare(assembly, directory / 'first', **arguments)
            second = prepare(assembly, directory / 'second', **arguments)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            with ZipFile(first) as archive:
                package, = [name for name in archive.namelist() if name.endswith('/PackageContents.xml')]
                folder = PurePosixPath(package).parent
                manifest = ElementTree.fromstring(archive.read(package))
                module = manifest.find('.//ComponentEntry').attrib['ModuleName']
                module_path = folder / module
                addin = ElementTree.fromstring(archive.read(str(module_path))).find('AddIn')
                self.assertEqual(addin.attrib['Type'], 'DBApplication')
                self.assertEqual(addin.findtext('FullClassName'), 'Bsa.Revit.AutomationInventory')
                binary = module_path.parent / addin.findtext('Assembly').split('\\')[-1]
                self.assertCountEqual(archive.namelist(), [package, str(module_path), str(binary)])
                self.assertEqual(archive.read(str(binary)), assembly.read_bytes())

            request = first.with_name('inventory-request.json').read_bytes()
            activity = first.with_name('activity.json').read_bytes()
            receipt = json.loads(first.with_name('preparation.json').read_bytes())
            expected_model_hash = hashlib.sha256(model.read_bytes()).hexdigest()
            self.assertEqual(json.loads(request), {'SavedRvtSha256': expected_model_hash})
            self.assertEqual(receipt['request_sha256'], hashlib.sha256(request).hexdigest())
            self.assertEqual(receipt['activity_sha256'], hashlib.sha256(activity).hexdigest())
            self.assertEqual(receipt['saved_rvt_sha256'], expected_model_hash)
            parameters = json.loads(activity)['parameters']
            self.assertEqual({key: row['localName'] for key, row in parameters.items()}, {
                'model': 'input.rvt', 'request': 'inventory-request.json', 'inventory': 'inventory.json',
            })
