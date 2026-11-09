import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.rectangular_model_design import resize,run
from bsa.workflow import execute
from bsa.workflow_status import diagnose
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'


class RectangularModelDesignTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.names=('binding-project.json','undersized-wall.json','binding.json','single-catalogue.json','wall-options.json')
        for name in (*self.names,'brief.md','model-design-plan.json'):(self.root/name).write_bytes((EX/name).read_bytes())
        self.data=[json.loads((self.root/name).read_text()) for name in self.names]

    def test_actual_fixed_endpoints_stable_ids_and_bound_rerun(self):
        before=[(self.root/name).read_bytes() for name in self.names]
        r=run(*(self.root/name for name in self.names),self.root/'out')
        self.assertTrue(r['calculated_checks_pass']);self.assertTrue(r['fixed_endpoints_pass']);self.assertTrue(r['stable_object_port_ids_match'])
        d=json.loads((self.root/'out/selected-model.json').read_text())['devices'][0]
        self.assertEqual(d['properties']['InternalWidth_m'],.5)
        self.assertEqual([(self.root/name).read_bytes() for name in self.names],before)
        baseline=json.loads((self.root/'out/sizing/design-comparison.json').read_text())['baseline']
        self.assertFalse(baseline['calculated_checks_pass'])

    def test_resize_preserves_source_and_world_endpoints(self):
        _,m,b,c,g=self.data;before=copy.deepcopy(m);r=resize(m,b,{'MAIN':'large'},c,g)
        self.assertEqual(m,before)
        for old,new in zip(m['devices'][0]['ports'],r['devices'][0]['ports']):
            a=[x+y for x,y in zip(m['devices'][0]['origin_m'],old['offset_m'])]
            z=[x+y for x,y in zip(r['devices'][0]['origin_m'],new['offset_m'])]
            for x,y in zip(a,z):self.assertAlmostEqual(x,y)

    def test_space_rejected_choice_is_retained_and_cannot_be_selected(self):
        _,m,_,_,_=self.data
        m['spaces'][0]['size_m'][1]=1.31
        (self.root/'undersized-wall.json').write_text(json.dumps(m))
        r=run(*(self.root/name for name in self.names),self.root/'out')
        self.assertFalse(r['calculated_checks_pass']);self.assertIsNone(r['selected'])
        self.assertTrue(any(row['option']=='large' for row in r['rejected_geometry_options']))
        self.assertFalse((self.root/'out/selected-model.json').exists())

    def test_workflow_positive_and_no_feasible_blocking(self):
        for label,allowed in (('positive',['small','medium','large']),('negative',['small'])):
            c=copy.deepcopy(self.data[3]);c['allowed_options']['MAIN']=allowed
            (self.root/'single-catalogue.json').write_text(json.dumps(c))
            execute(self.root/'model-design-plan.json',self.root/label)
            rows=diagnose(self.root/'model-design-plan.json',self.root/label)['tasks']
            self.assertEqual([r['status'] for r in rows],['pass' if label=='positive' else 'fail','pending'])
            if label=='negative':self.assertEqual(rows[1]['blocked_by'],['air'])
