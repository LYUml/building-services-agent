import json
import unittest
from bsa.cli import digest
from bsa.documents import extract
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.spatial_terminal_preview import run as preview
from tests import test_spatial_terminal_inlet_workflow as fixtures

class StubWorkflowTests(unittest.TestCase):
    def test_latest_model_clearance_failure_and_disabled_gates(self):
        fixture=fixtures.InletWorkflowTests();f,plan=fixture.setup_plan();self.addCleanup(fixture.doCleanups)
        inlets=json.loads((f.plan.parent/'inlets.json').read_text());basis={name:dict(length_m=dict(value=.15,unit='m',source='Synthetic stub length',classification='design_choice'),internal_diameter_m=dict(value=row['diameter_m']['value'],unit='m',source='Synthetic bore matches nominal assumption',classification='assumed'),wall_thickness_m=dict(value=.0008,unit='m',source='Synthetic wall choice',classification='design_choice')) for name,row in inlets.items()};(f.plan.parent/'stubs.json').write_text(json.dumps(basis))
        index=next(i for i,t in enumerate(plan['tasks']) if t['id']=='coordination');plan['tasks'].insert(index,dict(id='stubs',kind='spatial_terminal_stubs',depends_on='inlets',basis='stubs.json'));plan['tasks'][index+1]['depends_on']='stubs';next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('stubs')
        brief=f.plan.parent/plan['brief'];brief.write_text(brief.read_text()+'\nAuthor source-classified hollow inlet stubs with open upstream boundaries.\n');row=extract(brief)['passages'][-1];plan['brief_sha256']=digest(brief);plan['passage_dispositions'][row['id']]='requirement';plan['requirements'].append(dict(id='Rstubs',passage=row['id'],quote=row['text'],task='stubs',acceptance=row['text']));f.plan.write_text(json.dumps(plan))
        for name,disabled in [('native',False),('disabled',True)]:
            out=f.root/name;r=execute(f.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'},disabled_module_providers=['ifcopenshell.polygon-spaces'] if disabled else [])
            self.assertTrue(verify(out)['integrity_pass']);context(f.plan,out);self.assertEqual(r['tasks']['stubs']['status'],'pending' if disabled else 'pass');self.assertEqual(r['tasks']['coordination']['status'],'pending' if disabled else 'fail');self.assertEqual(r['tasks']['independent-electrical']['status'],'pass');self.assertEqual(r['tasks']['review']['status'],'pending')
            if not disabled:
                report=json.loads((out/'coordination/terminal-coordination.json').read_text());self.assertEqual(report['terminal_ifc'],str(out/'stubs/terminal-stubs.json'));self.assertGreater(report['calculation']['clearance_violation_pair_count'],0)
                image=preview(out/'stubs/terminal-stubs.json',f.root/'stub-preview');self.assertEqual(len(image['preview']['ports']),3);self.assertEqual(len(image['preview']['context_ports_not_drawn']),8)
                self.assertIn('coordination (fail)',r['tasks']['review']['scope'])

