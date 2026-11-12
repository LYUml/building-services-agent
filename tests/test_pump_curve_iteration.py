import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest

from bsa import catalogue_iteration as iteration
from bsa.catalogue_iteration_verify import verify

ROOT=Path(__file__).resolve().parents[1]


class PumpCurveIterationTests(unittest.TestCase):
    def test_converged_insufficient_direct_curve_preserves_ordinary_review_gap(self):
        from tests.test_pump import case
        from bsa.workflow_draft import draft
        from bsa import workflow
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);brief=root/'brief.md'
            brief.write_text('Evaluate the declared synthetic laminar pump/network operating point without changing minimum flow.\n\nReview real equipment and installation separately.')
            plan=root/'plan.json';draft(brief,plan)
            source=json.loads(plan.read_text());network,weak,_=case(1.2e-6);_,good,_=case()
            for name,data in [('network.json',network),('weak.json',weak),('good.json',good)]:
                (root/name).write_text(json.dumps(data))
            source['tasks']=[dict(id='pump',kind='pump_operating_point',project='network.json',curve='weak.json'),dict(id='review',kind='manual',requires_pass=['pump'])]
            for row,task in zip(source['requirements'],['pump','review']):row.update(task=task,acceptance=row['quote'])
            row=source['requirements'][1]
            source['unresolved_inputs']=[dict(id='actual-equipment',kind='missing',description='Actual equipment is not supplied.',sources=[dict(passage=row['passage'],quote=row['quote'])],blocks_tasks=['review'])]
            plan.write_text(json.dumps(source));workflow.execute(plan,root/'original')
            baseline=json.loads((root/'original/pump/pump.json').read_text())
            self.assertEqual(baseline['status'],'converged')
            self.assertFalse(baseline['checks']['minimum_design_flow'])
            self.assertTrue(baseline['selected_rerun_pass'])
            result=iteration.run(plan,root/'original','pump',root/'good.json',root/'new-plan.json',root/'iteration')
            self.assertEqual(result['stage_errors'],{})
            self.assertTrue(verify(root/'iteration')['integrity_pass'])
            revised=json.loads((root/'new-plan.json').read_text())
            self.assertEqual(revised['unresolved_inputs'],source['unresolved_inputs'])
            report=json.loads((root/'iteration/workflow/workflow.json').read_text())
            self.assertEqual(report['tasks']['pump']['status'],'pass')
            self.assertEqual(report['tasks']['review']['status'],'pending')

    def actual(self,weak=False):
        temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(temp.cleanup)
        root=Path(temp.name)/'project'
        result=runpy.run_path(str(ROOT/'scripts/run_pump_curve_iteration_demo.py'))['execute'](root,weak)
        self.assertEqual(result['stage_errors'],{});self.assertTrue(result['verification']['integrity_pass'])
        original=json.loads((root/'coupled-plan.json').read_text())
        revised=json.loads((root/'revised-plan.json').read_text())
        expected=copy.deepcopy(original);next(t for t in expected['tasks'] if t['id']=='pump')['curve']='revised-pump-curve.json'
        self.assertEqual(revised,expected)
        self.assertEqual(len(revised['requirements']),8)
        return root,result

    def test_passing_revision_reexecutes_electrical_ifc_and_drawing_without_changing_targets(self):
        root,result=self.actual()
        report=json.loads((root/'iteration/workflow/workflow.json').read_text())
        self.assertTrue(all(t['status']=='pass' for t in report['tasks'].values()))
        self.assertFalse(result['design_accepted'])
        coupled=json.loads((root/'iteration/workflow/coupled/pump-electrical.json').read_text())
        self.assertEqual(coupled['record']['baseline_electrical_kw'],.75)
        receipt=root/'iteration/iteration.json';before=receipt.read_bytes();data=json.loads(before)
        for mutation in ('requirements','pins'):
            changed=copy.deepcopy(data)
            if mutation=='requirements':changed['original_requirements'].pop()
            else:changed['inputs'].pop(str((root/'original-run/workflow.json').resolve()))
            receipt.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):verify(root/'iteration')
        receipt.write_bytes(before);self.assertTrue(verify(root/'iteration')['integrity_pass'])

    def test_insufficient_revision_retains_blockers_and_creates_no_coupled_model(self):
        root,result=self.actual(True)
        self.assertEqual(result['verification']['task_status'],'fail')
        report=json.loads((root/'iteration/workflow/workflow.json').read_text())
        for name in ('coupled','coupled-qa','coupled-drawing'):
            self.assertEqual(report['tasks'][name]['status'],'pending')
            self.assertFalse((root/'iteration/workflow'/name).exists())

    def test_direct_network_context_and_curve_only_revision(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);curve=root/'curve.json';network=root/'network.json'
            from tests.test_pump import case
            data,points,_=case()
            curve.write_text(json.dumps(points));network.write_text(json.dumps(data))
            task=dict(id='pump',kind='pump_operating_point',project='network.json',curve='old.json')
            source=dict(tasks=[task],requirements=[],unresolved_inputs=[])
            context,pins=iteration.selection_context(task,source,root/'plan.json',root/'run',curve)
            self.assertEqual(context,network);self.assertEqual(set(pins),{str(curve),str(network)})
            changed=iteration.revised_plan(source,'pump',curve,root/'new.json')
            self.assertEqual(changed['tasks'][0]['curve'],'curve.json')
            self.assertEqual(source['tasks'][0]['curve'],'old.json')


if __name__=='__main__':unittest.main()
