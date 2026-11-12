import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow_modules import inherited_request,inputs

ROOT=Path(__file__).resolve().parents[1]

class FrictionInheritanceTests(unittest.TestCase):
    def test_materialization_uses_exact_declared_stub_and_forbids_replacement(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temporary:
            root=Path(temporary);plan=root/'inputs';plan.mkdir();run=root/'run';(run/'stubs').mkdir(parents=True)
            stub=run/'stubs/terminal-stubs.json';stub.write_text('Synthetic binding control only;not native evidence');basis=plan/'basis.json';basis.write_text('{}')
            request=dict(schema='bsa.module-request/1',project_id='binding-control',scenario_id='inherited-friction',capability='analysis.air.native-stub-friction',coordinate_frame=dict(id='source-world',kind='source-world-si',length_unit='m',georeferenced=False),sources=dict(basis=dict(path=basis.name,sha256=digest(basis))))
            path=plan/'request.json';path.write_text(json.dumps(request));producer=dict(id='stubs',kind='spatial_terminal_stubs');task=dict(id='analysis',kind='module_analysis',depends_on='stubs',provider='fluids.native-stub-friction',request=path.name)
            destination,materialized=inherited_request(task,[producer,task],plan,run);selected=(destination.parent/materialized['sources']['stubs']['path']).resolve();self.assertEqual(selected,stub);self.assertEqual(materialized['sources']['stubs']['sha256'],digest(stub))
            request['sources']['stubs']=dict(path='replacement.json',sha256='0'*64);path.write_text(json.dumps(request))
            with self.assertRaisesRegex(ValueError,'replacement IFC forbidden'):inputs(path,task['provider'],inherited=True)
