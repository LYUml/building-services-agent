"""Request binding tests with non-RVT fixture bytes, never native execution."""
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.revit_request import prepare

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

    def test_unknown_selection_and_invalid_geometry_rejected(self):
        for field,value in (('PipeTypeUniqueId','invented'),('SystemTypeUniqueId','invented'),
                            ('LevelUniqueId','invented'),('DiameterMetres',True),('EndMetres',[0,0,0]),
                            ('StartMetres',[float('nan'),0,0])):
            with self.subTest(field=field),tempfile.TemporaryDirectory(dir=ROOT/'runs') as d:
                root=Path(d);inv,model,basis,_=self.fixture(root)
                data=json.loads(basis.read_text());data['pipe'][field]=value;basis.write_text(json.dumps(data))
                with self.assertRaises(ProjectError):prepare(inv,model,basis,root/'out')
                self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
