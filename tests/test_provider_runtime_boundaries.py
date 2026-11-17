import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.modules import verify_result
from bsa import modules
from bsa.providers import epanet_water
from tests import test_modular_water as fixtures


class RuntimeBoundaryTests(unittest.TestCase):
    def test_inherited_runtime_permission_is_exact_and_hash_bound(self):
        from bsa import runtime_evidence
        trusted=runtime_evidence.fluids_method_paths();self.assertEqual(len(trusted),2)
        with patch.object(runtime_evidence,'allowed',return_value=False):
            self.assertTrue(runtime_evidence.inherited_inputs_current({str(p):digest(p) for p in trusted}))
            p=next(iter(trusted))
            self.assertFalse(runtime_evidence.inherited_inputs_current({str(p):'0'*64}))
            unrelated=p.parent/'__init__.py'
            self.assertFalse(runtime_evidence.inherited_inputs_current({str(unrelated):digest(unrelated)}))

    def test_platform_selection_uses_installed_wntr_layout(self):
        for name,description,relative in [('win32','Windows','windows-x64/epanet22.dll'),('linux','Linux','linux-x64/libepanet22.so'),('darwin','arm Darwin','darwin-arm/libepanet2.dylib'),('darwin','x86 Darwin','darwin-x64/libepanet22.dylib')]:
            with self.subTest(platform=name,description=description),patch.object(epanet_water.sys,'platform',name),patch.object(epanet_water.platform,'platform',return_value=description):
                self.assertTrue(epanet_water.native_library().as_posix().endswith('/'+relative))

    def test_trusted_runtime_pin_cannot_authorize_external_project_source(self):
        fixture=fixtures.ModularWaterTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        out,_,result=fixture.scenario();self.assertEqual(result['execution']['status'],'completed')
        path=out/'water/result.json';original=copy.deepcopy(result)
        with tempfile.TemporaryDirectory() as temporary:
            external=Path(temporary)/'unrelated.txt';external.write_text('Controlled unrelated external file')
            result['inputs'][str(external.resolve())]=digest(external);path.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError,'Module input evidence changed'):verify_result(path)
        result=original
        library=epanet_water.native_library()
        request=json.loads(fixture.request.read_text())
        request['sources']['project']=dict(path=os.path.relpath(library,fixture.request.parent),sha256=digest(library))
        fixture.request.write_text(json.dumps(request))
        result['request']['sha256']=digest(fixture.request);result['inputs'][str(fixture.request)]=digest(fixture.request)
        path.write_text(json.dumps(result))
        allowed=modules.allowed
        with patch.object(modules,'allowed',side_effect=lambda p:Path(p).resolve()!=library and allowed(p)):
            with self.assertRaisesRegex(ValueError,'source outside selected workspace'):verify_result(path)
