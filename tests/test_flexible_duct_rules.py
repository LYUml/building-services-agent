import copy
import json
from pathlib import Path
import tempfile
import unittest

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.regulations import evaluate,method_paths,run

ROOT=Path(__file__).resolve().parents[1]


class FlexibleDuctRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pack=json.loads((ROOT/'regulations/hk/flex-routing-2026.11.11/pack.json').read_text())
        self.source=self.root/self.pack['sources']['fsd_mv_2023']['cache_filename']
        self.source.write_bytes(b'Synthetic source pin fixture;not an official regulation PDF')
        self.pack['sources']['fsd_mv_2023']['sha256']=digest(self.source)
        self.project=dict(jurisdiction='HK',rule_pack=self.pack['id'],
            edition_decisions=dict(fsd_mv_2023=dict(edition='Circular 2/2023',basis='Synthetic applicability control')),
            facts=dict(mechanical_ventilating_system_scope_confirmed=dict(value=True,source='Synthetic scope')),
            flexible_duct_inventory=dict(source='Synthetic complete inventory',complete=True,connections=[dict(
                id='F1',source='Synthetic individual connection',role='final_connection',penetrations_complete=True,
                penetrations=[],ends=[dict(kind='other',source='Synthetic end A'),dict(kind='other',source='Synthetic end B')])]))

    def check(self):return evaluate(self.pack,self.project,self.root)

    def test_clear_sourced_inventory_passes_only_supported_assertion_checks(self):
        result=self.check()
        self.assertTrue(result['supported_checks_pass']);self.assertFalse(result['design_accepted'])
        self.assertEqual(result['regulatory_compliance'],'not_established')
        self.assertTrue(all(r['binding_status']=='sourced_inventory_assertions_only' for r in result['checks']))
        self.assertTrue(all(r['known_forbidden_connection_count']==0 for r in result['checks']))

    def test_each_prohibition_blocks_without_a_length_override(self):
        original=copy.deepcopy(self.project)
        for case,index in [('main',0),('wall',1),('floor',1),('ceiling',1),('partition',1),('fire_damper',2),('fire_smoke_damper',2)]:
            self.project=copy.deepcopy(original);connection=self.project['flexible_duct_inventory']['connections'][0]
            if case=='main':connection['role']='main_distribution'
            elif index==1:connection['penetrations']=[dict(id='B1',kind=case,fire_resisting=True,source='Synthetic boundary')]
            else:connection['ends'][1]['kind']=case
            self.project['facts']['maximum_complete_connection_length']=dict(value=1,unit='m',source='Short synthetic connection')
            result=self.check()
            with self.subTest(case=case):
                self.assertEqual(result['checks'][index]['status'],'review_required')
                self.assertEqual(result['checks'][index]['known_forbidden_connection_count'],1)
                self.assertFalse(result['supported_checks_pass'])

    def test_unknown_and_incomplete_inventory_cannot_pass_or_become_inapplicable(self):
        original=copy.deepcopy(self.project)
        for case in ('complete_false','missing','role','boundary','end'):
            self.project=copy.deepcopy(original)
            inventory=self.project['flexible_duct_inventory'];connection=inventory['connections'][0]
            if case=='complete_false':inventory['complete']=False
            elif case=='missing':self.project.pop('flexible_duct_inventory')
            elif case=='role':connection['role']=None
            elif case=='boundary':connection['penetrations_complete']=None
            else:connection['ends'][0]['kind']=None
            result=self.check()
            with self.subTest(case=case):
                self.assertFalse(result['supported_checks_pass'])
                self.assertIn('pending',[r['status'] for r in result['checks']])
                self.assertNotIn('not_applicable',[r['status'] for r in result['checks']])
        self.project=copy.deepcopy(original)
        inventory=self.project['flexible_duct_inventory'];inventory['complete']=False
        inventory['connections'][0]['role']='main_distribution'
        result=self.check()
        self.assertEqual(result['checks'][0]['status'],'review_required')
        self.assertTrue(result['checks'][0]['unresolved_inventory_conditions'])

    def test_aggregate_zero_cannot_replace_individual_inventory_and_source_guards_apply(self):
        for rule in self.pack['rules']:
            self.project['facts'][rule['metric']]=dict(value=0,unit='connections',source='Forged aggregate')
        self.project['flexible_duct_inventory']['connections'][0]['role']='main_distribution'
        self.assertEqual(self.check()['checks'][0]['status'],'review_required')
        self.project['edition_decisions']={}
        self.assertTrue(all(r['status']=='pending' for r in self.check()['checks']))
        self.source.write_bytes(b'Changed source')
        self.assertFalse(self.check()['supported_checks_pass'])

    def test_invalid_identity_class_and_endpoint_schema_reject(self):
        original=copy.deepcopy(self.project)
        for case in ('duplicate','role','boundary','end'):
            self.project=copy.deepcopy(original);rows=self.project['flexible_duct_inventory']['connections']
            if case=='duplicate':rows.append(copy.deepcopy(rows[0]))
            elif case=='role':rows[0]['role']='anything'
            elif case=='boundary':rows[0]['penetrations']=[dict(id='B',kind='wall',fire_resisting='false',source='Synthetic')]
            else:rows[0]['ends'][0]['kind']='anything'
            with self.subTest(case=case),self.assertRaises(ProjectError):self.check()

    def test_standalone_method_pins_and_mixed_pack_inventory(self):
        for name,data in [('pack.json',self.pack),('project.json',self.project)]:
            (self.root/name).write_text(json.dumps(data))
        result=run(self.root/'pack.json',self.root/'project.json',self.root,self.root/'out')
        self.assertTrue(result['inputs_unchanged'])
        self.assertIn(str((ROOT/'src/bsa/flexible_duct_rules.py').resolve()),result['inputs'])
        methods=method_paths(dict(rules=[dict(method='base_air_distribution_fan_power'),dict(method='flexible_duct_restrictions')]))
        self.assertEqual({p.name for p in methods},{'regulations.py','fan_power_rules.py','flexible_duct_rules.py'})

    def test_workflow_method_binding_and_unknown_inventory_blocks_release(self):
        from bsa.workflow import execute,verify
        text='Check the scoped flexible-duct inventory and preserve independent engineering review.'
        brief=self.root/'brief.md';brief.write_text(text)
        (self.root/'pack.json').write_text(json.dumps(self.pack))
        self.project['flexible_duct_inventory']['complete']=None
        (self.root/'project.json').write_text(json.dumps(self.project))
        plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
            tasks=[dict(id='rules',kind='regulations',pack='pack.json',project='project.json',sources='.'),
                dict(id='review',kind='manual',description='Independent full engineering review',requires_pass=['rules'])],
            requirements=[dict(id='R'+str(i),task=task,passage='P001',quote=text,acceptance=text) for i,task in enumerate(('rules','review'))])
        path=self.root/'plan.json';path.write_text(json.dumps(plan))
        result=execute(path,self.root/'workflow')
        self.assertEqual(result['tasks']['rules']['status'],'pending')
        self.assertIn('required checks unresolved',result['tasks']['review']['scope'])
        self.assertIn(str((ROOT/'src/bsa/flexible_duct_rules.py').resolve()),result['inputs'])
        self.assertTrue(verify(self.root/'workflow')['integrity_pass'])
