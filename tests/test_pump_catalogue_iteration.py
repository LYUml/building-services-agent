import copy
import json
from pathlib import Path
import tempfile
import unittest

from bsa import pump_catalogue_iteration as selection,workflow
from bsa.workflow_draft import draft
from bsa.cli import digest
from tests.test_pump import case

ROOT=Path(__file__).resolve().parents[1]


class PumpCatalogueIterationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.plan=self.root/'plan.json';self.out=self.root/'screen';self.target=self.root/'new-plan.json'
        brief=self.root/'brief.md';brief.write_text('Calculate the synthetic pump operating point with the original minimum flow.\n\nReview actual equipment and installation.')
        draft(brief,self.plan);source=json.loads(self.plan.read_text())
        network,weak,_=case(1.2e-6);_,self.good,_=case()
        (self.root/'network.json').write_text(json.dumps(network));(self.root/'weak.json').write_text(json.dumps(weak))
        source['tasks']=[dict(id='pump',kind='pump_operating_point',project='network.json',curve='weak.json'),dict(id='review',kind='manual',requires_pass=['pump'])]
        for row,task in zip(source['requirements'],['pump','review']):row.update(task=task,acceptance=row['quote'])
        source['unresolved_inputs']=[];self.plan.write_text(json.dumps(source))
        workflow.execute(self.plan,self.root/'original')
        self.catalogue=self.root/'catalogue.json'
        self.data=dict(objective=selection.preference.OBJECTIVE,source='Explicit synthetic analytic curves, not real equipment',candidates=[dict(id='weak',source='Synthetic insufficient flow',preference=0,curve=weak),dict(id='eligible',source='Synthetic eligible curve',preference=1,curve=self.good)])

    def run_selection(self,**options):
        self.catalogue.write_text(json.dumps(self.data))
        return selection.run(self.plan,self.root/'original','pump',self.catalogue,self.target,self.out,**options)

    def test_electrical_mode_cannot_bind_an_unrelated_original_task(self):
        with self.assertRaisesRegex(ValueError,'downstream pump-electrical'):self.run_selection(electrical_task='review')
        self.assertFalse(self.out.exists());self.assertFalse(self.target.exists())

    def test_selects_passing_curve_and_runs_original_graph_with_pending_review(self):
        before=self.plan.read_bytes();result=self.run_selection();checked=selection.verify(self.out)
        self.assertEqual(checked['selected'],'eligible');self.assertTrue(checked['full_plan_executed'])
        self.assertFalse(result['design_accepted']);self.assertEqual(self.plan.read_bytes(),before)
        report=json.loads((self.out/'replay/workflow/workflow.json').read_text())
        self.assertEqual(report['tasks']['pump']['status'],'pass');self.assertEqual(report['tasks']['review']['status'],'pending')
        self.assertEqual(json.loads(self.target.read_text())['requirements'],json.loads(before)['requirements'])

    def test_no_eligible_curve_never_creates_new_plan_or_replay(self):
        self.data['candidates']=self.data['candidates'][:1]
        result=self.run_selection();self.assertEqual(result['status'],'no_feasible_candidate')
        self.assertIsNone(selection.verify(self.out)['selected'])
        self.assertFalse(self.target.exists());self.assertFalse((self.out/'replay').exists())

    def test_source_replayed_rank_and_candidate_curve_reject_rehashed_tampering(self):
        self.data['candidates'].append(dict(id='lexically-first',source='Same synthetic curve',preference=1,curve=self.good))
        self.run_selection();receipt=self.out/'selection.json';before=receipt.read_bytes();record=json.loads(before)
        self.assertEqual(selection.verify(self.out)['selected'],'eligible')
        forged=copy.deepcopy(record);forged['screening']['selected']['id']='weak';receipt.write_text(json.dumps(forged))
        with self.assertRaises(ValueError):selection.verify(self.out)
        receipt.write_bytes(before)
        curve=self.out/'candidate-000/curve.json';curve.write_text(json.dumps(self.good))
        record['artifacts']['candidate-000/curve.json']=digest(curve);receipt.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'candidate curve'):selection.verify(self.out)

    def test_invalid_catalogue_and_outside_output_reject_before_creation(self):
        for mutate in (lambda d:d['candidates'].append(copy.deepcopy(d['candidates'][0])),lambda d:d.update(command='untrusted'),lambda d:d['candidates'][0].update(preference=True)):
            data=copy.deepcopy(self.data);mutate(data)
            with self.assertRaises(ValueError):selection.candidates(data)
        self.catalogue.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):selection.run(self.plan,self.root/'original','pump',self.catalogue,self.target,ROOT/'runs/outside-pump-selection')
        self.assertFalse(self.out.exists())


if __name__=='__main__':unittest.main()
