import json
import unittest
from bsa.workflow import execute,verify
from bsa.delivery import context
from bsa.documents import extract
from bsa.cli import digest
from bsa.spatial_terminal_preview import run as preview
from tests import test_spatial_terminal_bim_workflow as fixtures

class InletWorkflowTests(unittest.TestCase):
    def setup_plan(self):
        fixture=fixtures.TerminalBIMWorkflowTests();f=fixture.setup_plan();self.addCleanup(fixture.doCleanups)
        names=json.loads((f.plan.parent/'envelopes.json').read_text())
        basis={name:dict(offset_m=dict(value=[.3,.3,.1],unit='m',source='Synthetic top face',classification='design_choice'),outward_axis=dict(value=[0,0,1],unit='1',source='Synthetic outward axis',classification='design_choice'),diameter_m=dict(value=.2,unit='m',source='Synthetic nominal diameter',classification='assumed'),system=dict(id='Trial Air',predefined_type='VENTILATION',source='Synthetic group',classification='design_choice')) for name in names}
        (f.plan.parent/'inlets.json').write_text(json.dumps(basis));plan=json.loads(f.plan.read_text());index=next(i for i,t in enumerate(plan['tasks']) if t['id']=='coordination');plan['tasks'].insert(index,dict(id='inlets',kind='spatial_terminal_inlets',depends_on='model',basis='inlets.json'));plan['tasks'][index+1]['depends_on']='inlets';next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('inlets')
        brief=f.plan.parent/plan['brief'];brief.write_text(brief.read_text()+'\nAdd sourced logical inlet ports without physical duct connections.\n');row=extract(brief)['passages'][-1];plan['brief_sha256']=digest(brief);plan['passage_dispositions'][row['id']]='requirement';plan['requirements'].append(dict(id='Rinlets',passage=row['id'],quote=row['text'],task='inlets',acceptance=row['text']));f.plan.write_text(json.dumps(plan))
        return f,plan

    def test_exact_inlet_model_consumption_preview_and_disabled_gates(self):
        f,plan=self.setup_plan()
        for name,disabled in [('native',False),('disabled',True)]:
            out=f.root/name;r=execute(f.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'},disabled_module_providers=['ifcopenshell.polygon-spaces'] if disabled else [])
            self.assertTrue(verify(out)['integrity_pass']);context(f.plan,out);self.assertEqual(r['tasks']['coordination']['status'],'pending' if disabled else 'pass');self.assertEqual(r['tasks']['inlets']['status'],'pending' if disabled else 'pass');self.assertEqual(r['tasks']['independent-electrical']['status'],'pass')
            if not disabled:
                report=json.loads((out/'coordination/terminal-coordination.json').read_text());self.assertEqual(report['terminal_ifc'],str(out/'inlets/terminal-inlets.json'))
                image=preview(out/'inlets/terminal-inlets.json',f.root/'preview');self.assertEqual(len(image['preview']['ports']),3);self.assertEqual(len(image['preview']['context_ports_not_drawn']),2)
                # Even coherent upstream evidence from the older envelope file must not replace the declared inlet producer.
                from bsa.spatial_terminal_coordination import run as coordinate
                alternate=f.root/'alternate';coordinate(out/'model/terminal-ifc.json',f.plan.parent/'policy.json',alternate)
                import shutil
                shutil.copyfile(alternate/'terminal-coordination.json',out/'coordination/terminal-coordination.json')
                from bsa.spatial_terminal_coordination import verify_workflow as verify_binding
                with self.assertRaisesRegex(ValueError,'declared inputs'):verify_binding(plan['tasks'],out,f.plan.parent,r['tasks'])
                with self.assertRaises(ValueError):context(f.plan,out)
