import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.duct_plan_clearance import from_workflow
from tests import test_duct_plan_clearance as fixtures


class InheritedPlanTests(unittest.TestCase):
    def test_inheritance_scope_and_rejected_replacements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();directory=root/'workflow';(directory/'native/reopened').mkdir(parents=True)
            (directory/'schedule').mkdir()
            fixture=fixtures.PlanClearanceTests()
            doc,schedule,binding,original=fixture.fixture(lower=.75)
            doc.saveas(directory/'native/reopened/source-export.dxf')
            project=root/'project.json';project.write_text('{}')
            schedule['input_sha256']=digest(project)
            (directory/'schedule/results.json').write_text(json.dumps(schedule))
            (root/'binding.json').write_text(json.dumps(binding))
            tasks=[dict(id='schedule',kind='duct_schedule',project='project.json'),
                   dict(id='sheet',kind='duct_sheet',depends_on='schedule',binding='binding.json'),
                   dict(id='native',kind='duct_sheet_native',depends_on='sheet')]
            plan=root/'plan.json';plan.write_text(json.dumps(dict(tasks=tasks)))
            report=dict(inputs={str(plan):digest(plan)},tasks={t['id']:dict(status='pass') for t in tasks})
            manifest=directory/'workflow.json';manifest.write_text(json.dumps(report))
            settings={k:original[k] for k in ('clearance_m','basis','obstacles')}
            settings.update(native_task='native',coverage=dict(complete=False,unresolved=['Synthetic omitted wall']))
            config=root/'settings.json';config.write_text(json.dumps(settings))
            # Verify ancestry/binding behavior here; real integrity/native execution is covered by the actual package run.
            with patch('bsa.workflow.verify',return_value={'integrity_pass':True}):
                r=from_workflow(plan,directory,config,root/'review.json')
                self.assertEqual(r['lineage'],['native','sheet','schedule'])
                self.assertTrue(r['planar_target_met'])
                self.assertFalse(r['coverage']['complete'])
                self.assertEqual(r['status'],'review_required')
                self.assertFalse(r['design_accepted'])
                settings['drawing']='replacement.dxf';config.write_text(json.dumps(settings))
                with self.assertRaisesRegex(ValueError,'settings require'):
                    from_workflow(plan,directory,config,root/'replacement.json')
                del settings['drawing'];settings['coverage']['complete']=True;config.write_text(json.dumps(settings))
                with self.assertRaisesRegex(ValueError,'contradicts'):
                    from_workflow(plan,directory,config,root/'coverage.json')
                settings['coverage']['complete']=False;config.write_text(json.dumps(settings))
                report['tasks']['native']['status']='pending';manifest.write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError,'Passing native'):
                    from_workflow(plan,directory,config,root/'pending.json')
            with patch('bsa.workflow.verify',return_value={'integrity_pass':False}):
                with self.assertRaisesRegex(ValueError,'artifacts changed'):
                    from_workflow(plan,directory,config,root/'stale.json')
