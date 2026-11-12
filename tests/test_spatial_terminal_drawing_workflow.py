import json
import unittest
from bsa.workflow import execute,verify,validate_plan
from bsa.delivery import context
from bsa.spatial_terminal_drawing import verify as verify_drawing
from tests import test_spatial_terminal_performance as fixtures

class SpatialDrawingWorkflowTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.SpatialTerminalPerformanceTests();f.setUp();self.addCleanup(f.temp.cleanup);self.f=f
        settings=f.plan.parent/'drawing-settings.json';settings.write_text(json.dumps(dict(annotation_height_m=.12,source='Synthetic annotation control')))
        plan=json.loads(f.plan.read_text());plan['tasks'].insert(-2,dict(id='drawing',kind='spatial_terminal_drawing',depends_on='terminal-allocation',settings=settings.name))
        next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('drawing')
        from bsa.documents import extract
        from bsa.cli import digest
        brief=f.plan.parent/plan['brief'];brief.write_text(brief.read_text()+'\nGenerate a source-bound terminal airflow schematic for review.\n')
        passage=extract(brief)['passages'][-1];plan['brief_sha256']=digest(brief);plan['passage_dispositions'][passage['id']]='requirement'
        plan['requirements'].append(dict(id='Rdraw',passage=passage['id'],quote=passage['text'],task='drawing',acceptance=passage['text']))
        f.plan.write_text(json.dumps(plan))

    def test_execution_and_disabled_provider_gate(self):
        for name,kwargs in [('native',{}),('disabled',dict(disabled_module_providers=['ifcopenshell.polygon-spaces']))]:
            out=self.f.root/name;record=execute(self.f.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'},**kwargs)
            self.assertTrue(verify(out)['integrity_pass']);context(self.f.plan,out)
            self.assertEqual(record['tasks']['drawing']['status'],'pass' if name=='native' else 'pending')
            self.assertEqual((out/'drawing/drawing.json').exists(),name=='native')
            self.assertEqual(record['tasks']['independent-electrical']['status'],'pass');self.assertEqual(record['tasks']['review']['status'],'pending')
            if name=='native':self.assertFalse(verify_drawing(out/'drawing')['native_reopen_pass'])

    def test_replacement_geometry_and_wrong_producer_rejected(self):
        plan=json.loads(self.f.plan.read_text());task=next(t for t in plan['tasks'] if t['id']=='drawing');task['allocation']='replacement.json';self.f.plan.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):validate_plan(self.f.plan)
        task.pop('allocation');task['depends_on']='air-balance';self.f.plan.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):validate_plan(self.f.plan)
