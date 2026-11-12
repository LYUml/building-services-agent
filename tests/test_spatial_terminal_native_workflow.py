import json
import unittest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.documents import extract
from bsa.cli import digest
from tests import test_spatial_terminal_drawing_workflow as fixtures

class SpatialNativeWorkflowTests(unittest.TestCase):
    def test_missing_runtime_and_disabled_geometry_remain_pending(self):
        fixture=fixtures.SpatialDrawingWorkflowTests();fixture.setUp();self.addCleanup(fixture.doCleanups);f=fixture.f
        settings=f.plan.parent/'spatial-native-settings.json';settings.write_text(json.dumps(dict(layers=['BSA_ROOM','BSA_TERMINAL_CENTER','BSA_FLOW','BSA_ROOM_LABEL'],sheet={})))
        plan=json.loads(f.plan.read_text());index=next(i for i,t in enumerate(plan['tasks']) if t['id']=='review');plan['tasks'].insert(index,dict(id='native',kind='spatial_terminal_native',depends_on='drawing',settings=settings.name))
        next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('native')
        brief=f.plan.parent/plan['brief'];brief.write_text(brief.read_text()+'\nVerify the inherited schematic in native AutoCAD.\n');passage=extract(brief)['passages'][-1];plan['brief_sha256']=digest(brief);plan['passage_dispositions'][passage['id']]='requirement';plan['requirements'].append(dict(id='Rnative',passage=passage['id'],quote=passage['text'],task='native',acceptance=passage['text']));f.plan.write_text(json.dumps(plan))
        for name,kwargs in [('no-runtime',{}),('disabled',dict(disabled_module_providers=['ifcopenshell.polygon-spaces']))]:
            out=f.root/name;r=execute(f.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'},**kwargs)
            self.assertTrue(verify(out)['integrity_pass']);context(f.plan,out);self.assertEqual(r['tasks']['native']['status'],'pending');self.assertFalse((out/'native/spatial-native.json').exists());self.assertEqual(r['tasks']['independent-electrical']['status'],'pass')

