import hashlib
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from xml.etree import ElementTree
from zipfile import ZipFile

from scripts.prepare_revit_automation_bundle import confirm_engine, prepare, verify_stage


class RevitAutomationBundleTests(unittest.TestCase):
    def test_windows_publish_retries_sharing_failure_without_replacing_output(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            directory = Path(temporary)
            assembly = directory / 'Bsa.Revit.Automation.dll'
            assembly.write_bytes(b'synthetic assembly')
            rename = Path.rename
            for destination_appears in (False, True):
                output = directory / str(destination_appears)
                failure = PermissionError('simulated Windows sharing failure')
                failure.winerror = 32
                attempts = []

                def publish(stage, target):
                    attempts.append(target)
                    if len(attempts) == 1:
                        if destination_appears:
                            target.mkdir()
                            (target / 'original.txt').write_text('preserve', encoding='utf-8')
                        raise failure
                    return rename(stage, target)

                with patch.object(Path, 'rename', publish), patch('scripts.prepare_revit_automation_bundle.sleep'):
                    if destination_appears:
                        with self.assertRaisesRegex(FileExistsError, 'output appeared'):
                            prepare(assembly, output)
                        self.assertEqual(len(attempts), 1)
                        self.assertEqual(list(output.iterdir()), [output / 'original.txt'])
                    else:
                        prepare(assembly, output)
                        self.assertEqual(len(attempts), 2)
                        self.assertTrue(verify_stage(output)['stage_verified'])

    def test_changed_input_does_not_publish_partial_bundle(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            directory = Path(temporary)
            assembly = directory / 'Bsa.Revit.Automation.dll'
            assembly.write_bytes(b'synthetic assembly')
            output = directory / 'published'
            with patch('scripts.prepare_revit_automation_bundle.inventory_request',
                       side_effect=[{'SavedRvtSha256': 'a'*64}, {'SavedRvtSha256': 'b'*64}]):
                with self.assertRaisesRegex(ValueError, 'RVT changed during preparation'):
                    prepare(assembly, output, model=directory / 'fixture.rvt')
            self.assertEqual(list(directory.iterdir()), [assembly])

    def test_engine_confirmation_requires_exact_engine_identity(self):
        with patch('scripts.prepare_revit_automation_bundle.HTTPSConnection') as factory:
            connection = factory.return_value
            response = connection.getresponse.return_value
            response.status = 200
            engine = 'Autodesk.Revit+2027'
            response.read.return_value = json.dumps({
                'id': engine, 'version': 1, 'productVersion': '2027', 'description': 'test',
            }).encode()
            self.assertEqual(confirm_engine(engine, 'synthetic-token'),
                             {'id': engine, 'version': 1, 'productVersion': '2027'})
            self.assertEqual(connection.request.call_args.args, ('GET', '/da/us-east/v3/engines/Autodesk.Revit%2B2027'))
            response.status = 401
            with self.assertRaisesRegex(ValueError, 'HTTP 401'):
                confirm_engine(engine, 'synthetic-token')
            response.status = 200
            response.read.return_value = b'{"id":"Autodesk.Revit+2026","version":1,"productVersion":"2026"}'
            with self.assertRaisesRegex(ValueError, 'did not identify'):
                confirm_engine(engine, 'synthetic-token')

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
            self.assertTrue(verify_stage(first.parent, model)['stage_verified'])
            extra_request = first.with_name('pipe-request.json')
            extra_request.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unexpected staged Automation files'):
                verify_stage(first.parent, model)
            extra_request.unlink()

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

            with ZipFile(second) as archive:
                members = {name: archive.read(name) for name in archive.namelist()}
            members[package] = members[package].replace(b'R2027', b'R2026')
            with ZipFile(second, 'w') as archive:
                for name, data in members.items():
                    archive.writestr(name, data)
            second_receipt = second.with_name('preparation.json')
            forged = json.loads(second_receipt.read_bytes())
            forged['archive_sha256'] = hashlib.sha256(second.read_bytes()).hexdigest()
            second_receipt.write_text(json.dumps(forged), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'loader manifest differs'):
                verify_stage(second.parent, model)

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
            modified = json.loads(activity)
            modified['parameters']['inventory']['localName'] = 'different.json'
            altered_activity = json.dumps(modified).encode()
            first.with_name('activity.json').write_bytes(altered_activity)
            receipt['activity_sha256'] = hashlib.sha256(altered_activity).hexdigest()
            first.with_name('preparation.json').write_text(json.dumps(receipt), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Activity differs'):
                verify_stage(first.parent, model)
