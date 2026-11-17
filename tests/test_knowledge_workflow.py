import copy
import json
from pathlib import Path
import unittest

from bsa.engineering_data.context import create
from bsa.knowledge.index import build, verify as verify_index
from bsa.module_contract import read_json
from bsa.source_refs import file_hash, reference
from bsa.workflow import execute, verify
from tests import test_knowledge


class KnowledgeWorkflowTests(unittest.TestCase):
    def setUp(self):
        fixture = test_knowledge.KnowledgeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.manifest, self.data = fixture.root, fixture.manifest, fixture.data
        self.save = fixture.save
        self.source = fixture.source
        self.brief = self.root/'brief.md'
        text = 'Find the synthetic method with exact sources; engineering review remains separate.'
        self.brief.write_text(text, encoding='utf-8')
        self.plan = self.root/'plan.json'
        self.plan_data = dict(version=1, brief='brief.md', brief_sha256=file_hash(self.brief),
            passage_dispositions={'P001':'requirement'}, tasks=[
                dict(id='library',kind='knowledge_index',manifest='manifest.json'),
                dict(id='lookup',kind='knowledge_query',depends_on='library',query=dict(text='airflow')),
                dict(id='review',kind='manual',requires_pass=['lookup'],description='Review applicability separately')])
        self.plan_data['requirements'] = [dict(id='R'+str(i), passage='P001', quote=text,
            task=t['id'], acceptance='Inspect original citation and decide applicability separately')
            for i,t in enumerate(self.plan_data['tasks'])]
        self.save(self.plan,self.plan_data)

    def test_build_lookup_and_delivery_preserve_pending_acceptance(self):
        out=self.root/'executed'
        result=execute(self.plan,out)
        self.assertEqual([r['status'] for r in result['tasks'].values()],['pass','pass','pending'])
        self.assertTrue(verify(out)['integrity_pass'])
        found=read_json(out/'lookup/query.json')
        self.assertEqual(len(found['hits']),1)
        self.assertEqual(found['hits'][0]['metadata']['source'],reference(self.source))
        self.assertTrue(all(r['acceptance_status']=='pending review' for r in result['requirements']))
        from bsa.delivery import context
        context(self.plan,out)
        self.assertFalse(result['design_accepted'])

    def test_prebuilt_index_can_be_reused_without_rebuilding(self):
        build(self.manifest,self.root/'saved')
        task=self.plan_data['tasks'][1]
        del task['depends_on'];task['index_receipt']='saved/receipt.json'
        self.plan_data['tasks']=self.plan_data['tasks'][1:]
        self.plan_data['requirements']=self.plan_data['requirements'][1:]
        self.save(self.plan,self.plan_data)
        before=file_hash(self.root/'saved/index.sqlite')
        result=execute(self.plan,self.root/'run')
        self.assertEqual(result['tasks']['lookup']['status'],'pass')
        self.assertEqual(file_hash(self.root/'saved/index.sqlite'),before)
        self.assertFalse((self.root/'run/library').exists())
        self.assertTrue(verify(self.root/'run')['integrity_pass'])

    def rehash(self,out,changed):
        report=read_json(out/'workflow.json')
        for name in changed:
            report['artifact_hashes'][name]=file_hash(out/name)
        self.save(out/'workflow.json',report)

    def test_coherently_rehashed_query_cannot_drop_or_invent_hits(self):
        out=self.root/'run';execute(self.plan,out)
        original=read_json(out/'lookup/query.json')
        for mode in ('drop','citation'):
            changed=copy.deepcopy(original)
            if mode=='drop':changed['hits']=[]
            else:changed['hits'][0]['text']='Invented engineering advice'
            self.save(out/'lookup/query.json',changed);self.rehash(out,['lookup/query.json'])
            checked=verify(out)
            self.assertFalse(checked['integrity_pass'])
            self.assertTrue(any('Saved knowledge query differs' in s for s in checked['issues']))

    def test_valid_foreign_manifest_index_cannot_replace_declared_producer(self):
        out=self.root/'run';execute(self.plan,out)
        other=self.root/'other.json';self.save(other,self.data)
        build(other,self.root/'foreign')
        for name in ('request.json','receipt.json','index.sqlite'):
            (out/'library'/name).write_bytes((self.root/'foreign'/name).read_bytes())
        self.assertTrue(verify_index(out/'library')['integrity_pass'])
        self.rehash(out,['library/'+n for n in ('request.json','receipt.json','index.sqlite')])
        self.assertFalse(verify(out)['integrity_pass'])

    def test_workflow_context_must_match_scoped_corpus_before_output(self):
        create('Synthetic corpus','baseline',self.root/'context.json')
        self.data['project_context']=reference(self.root/'context.json');self.save(self.manifest,self.data)
        create('Other synthetic project','baseline',self.root/'wrong-context.json')
        for context in (None,'wrong-context.json'):
            if context:self.plan_data['project_context']=context
            else:self.plan_data.pop('project_context',None)
            self.save(self.plan,self.plan_data)
            with self.assertRaises(ValueError):execute(self.plan,self.root/'rejected')
            self.assertFalse((self.root/'rejected').exists())
        self.plan_data['project_context']='context.json';self.save(self.plan,self.plan_data)
        self.assertEqual(execute(self.plan,self.root/'good')['tasks']['lookup']['status'],'pass')

    def test_missing_method_pin_or_original_source_plan_cannot_hide(self):
        out=self.root/'run';execute(self.plan,out)
        original=read_json(out/'workflow.json')
        for mode in ('method','plan'):
            report=copy.deepcopy(original)
            if mode=='plan':del report['source_plan']
            else:del report['inputs'][str(Path(__file__).resolve().parents[1]/'src/bsa/knowledge/workflow.py')]
            self.save(out/'workflow.json',report)
            self.assertFalse(verify(out)['integrity_pass'])

    def test_no_hits_does_not_clear_manual_review(self):
        self.plan_data['tasks'][1]['query']['text']='absent_literal_term'
        self.save(self.plan,self.plan_data)
        out=self.root/'run';result=execute(self.plan,out)
        self.assertEqual(read_json(out/'lookup/query.json')['hits'],[])
        self.assertEqual(result['tasks']['lookup']['status'],'pass')
        self.assertEqual(result['tasks']['review']['status'],'pending')
        self.assertTrue(verify(out)['integrity_pass'])

    def test_failed_index_blocks_lookup_and_retains_failure_evidence(self):
        self.source.write_text('',encoding='utf-8')
        self.data['sources'][0]['source']=reference(self.source);self.save(self.manifest,self.data)
        separate=self.root/'independent.md';separate.write_text('Independent airflow reference',encoding='utf-8')
        independent=copy.deepcopy(self.data);independent['sources'][0]['source']=reference(separate)
        self.save(self.root/'independent.json',independent)
        extra=[dict(id='other_library',kind='knowledge_index',manifest='independent.json'),
               dict(id='other_query',kind='knowledge_query',depends_on='other_library',query=dict(text='airflow'))]
        self.plan_data['tasks']+=extra
        for offset,task in enumerate(extra,3):
            requirement=copy.deepcopy(self.plan_data['requirements'][0]);requirement.update(id='R'+str(offset),task=task['id'])
            self.plan_data['requirements'].append(requirement)
        self.save(self.plan,self.plan_data)
        out=self.root/'run';result=execute(self.plan,out)
        self.assertEqual(result['tasks']['library']['status'],'fail')
        self.assertEqual(result['tasks']['lookup']['status'],'pending')
        self.assertFalse((out/'lookup').exists())
        self.assertTrue((out/'library/request.json').exists())
        self.assertEqual(result['tasks']['other_library']['status'],'pass')
        self.assertEqual(result['tasks']['other_query']['status'],'pass')
        self.assertTrue(verify(out)['integrity_pass'])
