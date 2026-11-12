import copy
import json
import unittest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.documents import extract
from bsa.cli import digest
from tests import test_spatial_terminal_performance as fixtures

class TerminalBIMWorkflowTests(unittest.TestCase):
    def setup_plan(self,overlap=False):
        f=fixtures.SpatialTerminalPerformanceTests();f.setUp();self.addCleanup(f.temp.cleanup)
        if overlap:
            path=f.plan.parent/'terminal-design-basis.json';data=json.loads(path.read_text());room=next(iter(data.values()));a=room['terminals'][0];b=copy.deepcopy(a);b['id']+='B';b['center_m'][0]+=.05;room['terminals'].append(b);path.write_text(json.dumps(data))
            path=f.plan.parent/'performance-selections.json';data=json.loads(path.read_text());data[b['id']]=copy.deepcopy(data[a['id']]);path.write_text(json.dumps(data))
        data=json.loads((f.plan.parent/'performance-selections.json').read_text());basis={name:dict(size_m=dict(value=[.6,.6,.1],unit='m',source='Synthetic envelope choice',classification='design_choice'),bottom_above_floor_m=dict(value=2.7,unit='m',source='Synthetic height assumption',classification='assumed')) for name in data}
        (f.plan.parent/'envelopes.json').write_text(json.dumps(basis));policy=dict(scope='all represented non-feature non-virtual IfcElements',sources={'test':'Synthetic50mm control;not regulation'},source='test',minimum_clearance_m=.05,intersection_tolerance_m=.0001,contact_tolerance_m=.0001,overlap_volume_tolerance_m3=1e-10,maximum_boolean_pairs=1000,allowed_contacts=[]);(f.plan.parent/'policy.json').write_text(json.dumps(policy))
        plan=json.loads(f.plan.read_text());brief=f.plan.parent/plan['brief']
        for task,text in [(dict(id='model',kind='spatial_terminal_ifc',depends_on='terminal-performance',basis='envelopes.json'),'Author classified terminal envelopes preserving original IFC entities.'),(dict(id='coordination',kind='spatial_terminal_coordination',depends_on='model',policy='policy.json'),'Check the complete authored model for intersections and clearance.')]:
            index=next(i for i,t in enumerate(plan['tasks']) if t['id']=='review');plan['tasks'].insert(index,task);next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append(task['id']);brief.write_text(brief.read_text()+'\n'+text+'\n');passage=extract(brief)['passages'][-1];plan['passage_dispositions'][passage['id']]='requirement';plan['requirements'].append(dict(id=task['id'],passage=passage['id'],quote=passage['text'],task=task['id'],acceptance=text))
        plan['brief_sha256']=digest(brief);f.plan.write_text(json.dumps(plan));return f

    def test_pass_disabled_and_collision_failure(self):
        for name,overlap,disabled in [('clear',False,False),('disabled',False,True),('collision',True,False)]:
            f=self.setup_plan(overlap);out=f.root/name;r=execute(f.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'},disabled_module_providers=['ifcopenshell.polygon-spaces'] if disabled else [])
            self.assertTrue(verify(out)['integrity_pass']);context(f.plan,out)
            self.assertEqual(r['tasks']['coordination']['status'],'pending' if disabled else 'fail' if overlap else 'pass')
            self.assertEqual((out/'model/terminal-ifc.json').exists(),not disabled);self.assertEqual(r['tasks']['independent-electrical']['status'],'pass');self.assertEqual(r['tasks']['review']['status'],'pending')
