import json
import os
from pathlib import Path
import unittest
from bsa.cli import digest
from bsa.modules import run,verify_result
from bsa.spatial_terminal_stubs import run as author_stubs
from bsa.workflow import execute
from tests import test_spatial_terminal_inlet_workflow as fixtures

class NativeFrictionProviderTests(unittest.TestCase):
    def test_native_projection_disable_and_engineering_acceptance_guard(self):
        fixture=fixtures.InletWorkflowTests();f,_=fixture.setup_plan();self.addCleanup(fixture.doCleanups)
        workflow=f.root/'source-workflow';execute(f.plan,workflow,module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        inlet=json.loads((workflow/'inlets/terminal-inlets.json').read_text());spec={row['terminal']:dict(length_m=dict(value=.15,unit='m',source='Synthetic short length',classification='design_choice'),internal_diameter_m=dict(value=row['diameter_m'],unit='m',source='Synthetic nominal bore assumption',classification='assumed'),wall_thickness_m=dict(value=.0008,unit='m',source='Synthetic wall choice',classification='design_choice')) for row in inlet['inlets']}
        basis=f.root/'stubs.json';basis.write_text(json.dumps(spec));source=f.root/'stubs';author_stubs(workflow/'inlets/terminal-inlets.json',basis,source)
        air=f.root/'air.json';air.write_text(json.dumps(dict(dynamic_viscosity_pa_s=dict(value=1.8e-5,unit='Pa.s',source='Synthetic viscosity',classification='assumed'),roughness_m=dict(value=.00009,unit='m',source='Synthetic roughness',classification='assumed'))))
        frame=json.loads((f.plan.parent/'native-request.json').read_text())['coordinate_frame'];request=dict(schema='bsa.module-request/1',project_id='synthetic-native-control',scenario_id='common-analysis',capability='analysis.air.native-stub-friction',coordinate_frame=frame,sources={key:dict(path=os.path.relpath(p,f.root),sha256=digest(p)) for key,p in [('stubs',source/'terminal-stubs.json'),('basis',air)]});path=f.root/'request.json';path.write_text(json.dumps(request))
        out=f.root/'module';result=run(path,'fluids.native-stub-friction',out);verify_result(out/'result.json');self.assertEqual(result['execution']['status'],'completed');self.assertEqual(result['payload']['case_count'],6);self.assertEqual(result['payload']['status'],'pass');self.assertEqual(result['acceptance']['status'],'pending');self.assertFalse(result['payload']['fully_developed_flow_verified'])
        disabled=f.root/'disabled';r=run(path,'fluids.native-stub-friction',disabled,disabled=True);verify_result(disabled/'result.json');self.assertEqual(r['execution']['status'],'unavailable');self.assertIsNone(r['payload']);self.assertFalse((disabled/'analysis').exists())
        result['acceptance']['status']='pass';(out/'result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError,'acceptance must remain pending'):verify_result(out/'result.json')
