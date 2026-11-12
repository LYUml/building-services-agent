import copy
import json
from pathlib import Path
import tempfile
import unittest

from bsa import circular_fan
from bsa.circular_fan_selection import run,run_selected
from bsa.rectangular_fan_selection import candidates,screen,eligibility
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class CircularFanScreeningTests(unittest.TestCase):
    def setUp(self):
        self.project=json.loads((ROOT/'examples/route-search/vertical-air-network.json').read_text())
        for n in self.project['nodes']:n['elevation_m']=0
        self.project['segments'][0].update(length_m=6.4,diameter_m=.2032,minor_k=.8)
        self.catalogue=json.loads((ROOT/'examples/route-search/circular-fan-catalogue.json').read_text())
        self.calls=[]

    def evaluate(self,row,name,mechanical=None):
        self.calls.append((row['id'],name))
        try:
            r,_=circular_fan.solve(self.project,row['curve'])
            record={k:r.get(k) for k in ('status','checks','operating_point','calculated_checks_pass')}
        except ProjectError as exc:record=dict(status='unsupported',calculated_checks_pass=False,reason=str(exc))
        return eligibility(record,mechanical)

    def test_shared_screen_retains_bad_candidates_and_reruns_preferred_valid_curve(self):
        result=screen(candidates(self.catalogue),self.evaluate)
        self.assertEqual(result['selected']['id'],'supported');self.assertTrue(result['calculated_checks_pass'])
        self.assertEqual([r['status'] for r in result['candidates']],['converged','unsupported','converged'])
        self.assertFalse(result['candidates'][0]['checks']['minimum_design_flow'])
        self.assertEqual(self.calls[-1],('supported','selected'))

    def test_no_feasible_curve_never_calls_selected_rerun(self):
        result=screen(candidates(self.catalogue)[:2],self.evaluate)
        self.assertEqual(result['status'],'fail');self.assertIsNone(result['selected'])
        self.assertFalse(any(name=='selected' for _,name in self.calls))

    def test_tie_break_and_unknown_preferred_mechanical_identity(self):
        good=candidates(self.catalogue)[-1];other=copy.deepcopy(good);other['id']='aaa'
        result=screen([good,other],self.evaluate);self.assertEqual(result['selected']['id'],'aaa')
        self.calls=[]
        result=screen([good,other],lambda row,name:self.evaluate(row,name,{'status':'pending'} if row['id']=='aaa' else {'status':'pass'}))
        self.assertEqual(result['status'],'pending');self.assertIsNone(result['selected']);self.assertEqual(result['unresolved_preference'],['aaa'])
        self.assertFalse(any(name=='selected' for _,name in self.calls))

    def test_selected_rerun_must_match_ranked_operating_point(self):
        def changed(row,name):
            record=self.evaluate(row,name)
            if name=='selected':record['operating_point']['flow_m3_s']+=.001
            return record
        with self.assertRaises(ProjectError):screen(candidates(self.catalogue),changed)

    def test_failed_native_pressure_and_nested_consumer_reject_before_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);pressure=root/'pressure';pressure.mkdir()
            (pressure/'route-pressure.json').write_text(json.dumps(dict(calculated_checks_pass=False,design_accepted=False)))
            with self.assertRaises(ProjectError):run(pressure,ROOT/'examples/route-search/circular-fan-catalogue.json',root/'selection')
            self.assertFalse((root/'selection').exists())
            with self.assertRaises(ProjectError):run_selected(root/'selection',pressure,ROOT/'examples/route-search/circular-fan-catalogue.json',root/'selection/consumer')
