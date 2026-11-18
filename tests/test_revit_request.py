"""Request binding tests with non-RVT fixture bytes, never native execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.revit_request import prepare, validate_automation_request

ROOT=Path(__file__).resolve().parents[1]


class RevitRequestTests(unittest.TestCase):
    def fixture(self,root):
        model=root/'fixture.rvt';model.write_bytes(b'NOT RVT: binding control')
        source=root/'brief.txt';source.write_text('Synthetic pipe: 2 m along X; diameter 0.05 m.')
        inventory=root/'inventory.json'
        inventory.write_text(json.dumps(dict(units='metres',document_path=str(model),saved_rvt_sha256=digest(model),
            pipe_types=[dict(unique_id='p')],system_types=[dict(unique_id='s')],levels=[dict(unique_id='l')])))
        basis=root/'basis.json';basis.write_text(json.dumps(dict(source=dict(path='brief.txt',sha256=digest(source),locator='line 1'),
            pipe=dict(PipeTypeUniqueId='p',SystemTypeUniqueId='s',LevelUniqueId='l',StartMetres=[0,0,0],EndMetres=[2,0,0],DiameterMetres=.05))))
        return inventory,model,basis,source

    def test_bound_request_keeps_inputs_and_does_not_claim_native_execution(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as d:
            root=Path(d);inv,model,basis,source=self.fixture(root)
            result=prepare(inv,model,basis,root/'out')
            request=json.loads((root/'out/pipe-request.json').read_text())
            self.assertEqual(json.loads(request['Source'])['sha256'],digest(source))
            self.assertEqual(json.loads(request['Source'])['basis_sha256'],digest(basis))
            self.assertEqual(request['SavedRvtSha256'],digest(model))
            self.assertEqual(request['EndMetres'],[2,0,0])
            self.assertFalse(result['native_executed'])
            with self.assertRaises(ProjectError):prepare(inv,model,basis,root/'out')

    def test_changed_source_or_model_rejected_before_output(self):
        for target in ('source','model'):
            with self.subTest(target=target), tempfile.TemporaryDirectory(dir=ROOT/'runs') as d:
                root=Path(d);inv,model,basis,source=self.fixture(root)
                (source if target=='source' else model).write_bytes(b'changed')
                with self.assertRaises(ProjectError):prepare(inv,model,basis,root/'out')
                self.assertFalse((root/'out').exists())

    def test_saved_model_replaced_during_request_preparation_leaves_no_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root = Path(directory)
            inventory, model, basis, _ = self.fixture(root)
            original_read = Path.read_text

            def replace_after_read(path, *args, **kwargs):
                content = original_read(path, *args, **kwargs)
                if path == basis:
                    model.write_bytes(b'changed while loading the design basis')
                return content

            with patch.object(Path, 'read_text', replace_after_read):
                with self.assertRaisesRegex(ProjectError, 'Input changed during preparation'):
                    prepare(inventory, model, basis, root/'out')
            self.assertFalse((root/'out').exists())

    def test_unknown_selection_and_invalid_geometry_rejected(self):
        for field,value in (('PipeTypeUniqueId','invented'),('SystemTypeUniqueId','invented'),
                            ('LevelUniqueId','invented'),('DiameterMetres',True),('EndMetres',[0,0,0]),
                            ('StartMetres',[float('nan'),0,0])):
            with self.subTest(field=field),tempfile.TemporaryDirectory(dir=ROOT/'runs') as d:
                root=Path(d);inv,model,basis,_=self.fixture(root)
                data=json.loads(basis.read_text());data['pipe'][field]=value;basis.write_text(json.dumps(data))
                with self.assertRaises(ProjectError):prepare(inv,model,basis,root/'out')
                self.assertFalse((root/'out').exists())

    def test_empty_malformed_and_duplicate_selection_rows_are_rejected(self):
        for rows in ([], [None], [{'unique_id': ' '}], [{'unique_id': 's'}, {'unique_id': 's'}]):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
                root = Path(directory)
                inventory, model, basis, _ = self.fixture(root)
                data = json.loads(inventory.read_text())
                data['system_types'] = rows
                inventory.write_text(json.dumps(data))
                with self.assertRaisesRegex(ProjectError, 'selection.*system_types'):
                    prepare(inventory, model, basis, root/'out')
                self.assertFalse((root/'out').exists())

    def test_finite_coordinates_with_overflowing_segment_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root = Path(directory)
            inventory, model, basis, _ = self.fixture(root)
            data = json.loads(basis.read_text())
            data['pipe'].update(StartMetres=[-1e308, 0, 0], EndMetres=[1e308, 0, 0])
            basis.write_text(json.dumps(data))
            with self.assertRaisesRegex(ProjectError, 'finite nonzero segment'):
                prepare(inventory, model, basis, root/'out')
            self.assertFalse((root/'out').exists())
            model_hash = digest(model)
            request = dict(data['pipe'], DocumentPath=str(model), Source='Synthetic overflow control',
                           SavedRvtSha256=model_hash)
            with self.assertRaisesRegex(ProjectError, 'finite nonzero segment'):
                validate_automation_request(request, model_hash)

    def test_pipe_segment_must_exceed_native_adapter_floor(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root = Path(directory)
            inventory, model, basis, _ = self.fixture(root)
            data = json.loads(basis.read_text())
            for length in (0.002, 0.00254):
                data['pipe']['EndMetres'] = [length, 0, 0]
                basis.write_text(json.dumps(data))
                with self.assertRaisesRegex(ProjectError, 'adapter floor of 2.54 mm'):
                    prepare(inventory, model, basis, root/'out')
                self.assertFalse((root/'out').exists())
            data['pipe']['EndMetres'] = [0.00255, 0, 0]
            basis.write_text(json.dumps(data))
            self.assertFalse(prepare(inventory, model, basis, root/'out')['native_executed'])


if __name__=='__main__':unittest.main()
