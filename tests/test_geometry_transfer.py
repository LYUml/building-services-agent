import json
from pathlib import Path
import tempfile
import unittest
from bsa.spatial_terminal_candidate_plan import geometry_transfer

ROOT=Path(__file__).resolve().parents[1]

class GeometryTransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        old=self.root/'old.json';old.write_text(json.dumps(dict(calculation=dict(rooms={'R':dict(allocation=dict(terminals=[dict(id='old')]))}))))
        self.before=self.root/'performance.json';self.before.write_text(json.dumps(dict(allocation_result=str(old))))
        self.candidate=self.root/'candidate';(self.candidate/'allocation').mkdir(parents=True);(self.candidate/'allocation/terminal-allocation.json').write_text(json.dumps(dict(calculation=dict(rooms={'R':dict(allocation=dict(terminals=[dict(id='new1'),dict(id='new2')]))}))))
        self.basis=self.root/'basis.json';self.basis.write_text(json.dumps({'old':dict(length_m=dict(value=.15,unit='m',source='Synthetic original-classification control only',classification='measured'))}))
        self.policy=self.root/'policy.json';self.spec=dict(source='Explicit synthetic new geometry choice',classification='design_choice',from_terminal_by_room={'R':'old'});self.policy.write_text(json.dumps(self.spec))
        self.plan=dict(tasks=[dict(id='performance',kind='spatial_terminal_performance'),dict(id='stubs',kind='spatial_terminal_stubs',depends_on='performance',basis='basis.json')])
    def transfer(self):return geometry_transfer(self.plan,self.root,dict(original=str(self.before)),self.candidate,'performance',self.policy)
    def test_new_id_coverage_and_original_classification_are_distinct(self):
        original=self.basis.read_bytes();new,bindings,pins=self.transfer()
        self.assertEqual(set(new['stubs']['basis']),{'new1','new2'})
        self.assertEqual(new['stubs']['basis']['new1']['length_m']['classification'],'design_choice')
        self.assertEqual(bindings['stubs']['new1']['original_basis']['length_m']['classification'],'measured')
        self.assertEqual(self.basis.read_bytes(),original);self.assertIn(str(self.policy),pins)
    def test_implicit_or_cross_room_geometry_selection_rejects(self):
        for field,value in [('classification','given'),('from_terminal_by_room',{}),('from_terminal_by_room',{'R':'another-room-terminal'})]:
            bad=dict(self.spec);bad[field]=value;self.policy.write_text(json.dumps(bad))
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.transfer()
    def test_omitted_policy_changes_no_geometry(self):
        self.assertEqual(geometry_transfer(self.plan,self.root,{},self.candidate,'performance',None),({},{},{}))

    def test_unclassified_original_template_rejects(self):
        record=json.loads(self.basis.read_text());del record['old']['length_m']['classification'];self.basis.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'source/classification'):self.transfer()
    def test_unrelated_geometry_branch_is_not_reassigned(self):
        self.plan['tasks'].append(dict(id='unrelated',kind='spatial_terminal_ifc',depends_on='another-performance',basis='basis.json'))
        transfers,bindings,_=self.transfer();self.assertEqual(set(transfers),{'stubs'});self.assertEqual(set(bindings),{'stubs'})

    def test_shared_system_metadata_stays_identical_across_room_templates(self):
        before=json.loads(self.before.read_text());old_path=Path(before['allocation_result']);old=json.loads(old_path.read_text());old['calculation']['rooms']['R2']=dict(allocation=dict(terminals=[dict(id='old2')]));old_path.write_text(json.dumps(old))
        path=self.candidate/'allocation/terminal-allocation.json';new=json.loads(path.read_text());new['calculation']['rooms']['R2']=dict(allocation=dict(terminals=[dict(id='new3')]));path.write_text(json.dumps(new))
        system=dict(id='Shared',predefined_type='AIRCONDITIONING',source='Synthetic shared grouping',classification='design_choice');self.basis.write_text(json.dumps({'old':dict(system=system),'old2':dict(system=system)}))
        self.spec['from_terminal_by_room']['R2']='old2';self.policy.write_text(json.dumps(self.spec));transfers,_,_=self.transfer();rows=transfers['stubs']['basis']
        self.assertEqual(rows['new1']['system'],rows['new3']['system'])
        self.assertIn('shared system Shared',rows['new1']['system']['source'])
