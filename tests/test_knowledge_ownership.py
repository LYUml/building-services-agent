"""Synthetic dependency controls; real document execution remains separate evidence."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from bsa.changes import core
from bsa.cli import digest
from bsa.knowledge.index import build
from bsa.module_contract import read_json
from bsa.source_refs import reference
from bsa.workflow import execute,verify
from tests import test_knowledge_workflow

ROOT=Path(__file__).resolve().parents[1]


class KnowledgeOwnershipTests(unittest.TestCase):
    def setUp(self):
        f=test_knowledge_workflow.KnowledgeWorkflowTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.root=f.root;self.plan=f.plan;self.data=f.plan_data;self.save=f.save
        self.other=self.root/'other.md';self.other.write_text('Synthetic static lighting source.',encoding='utf-8')
        other=copy.deepcopy(f.data);other['sources'][0].update(id='other',source=reference(self.other))
        self.save(self.root/'other-manifest.json',other)
        self.data['tasks'] += [dict(id='other_library',kind='knowledge_index',manifest='other-manifest.json'),
            dict(id='other_query',kind='knowledge_query',depends_on='other_library',query=dict(text='lighting'))]
        project=self.root/'electrical.json';project.write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
        request=dict(schema='bsa.module-request/1',project_id='synthetic-knowledge-control',scenario_id='baseline',
            capability='analysis.electrical.single-phase-circuits',
            coordinate_frame=dict(id='declared-metres',kind='source-world-si',length_unit='m',georeferenced=False),
            sources=dict(project=dict(path=project.name,sha256=digest(project))))
        self.save(self.root/'electrical-request.json',request)
        self.data['tasks'].append(dict(id='independent',kind='module_analysis',request='electrical-request.json',provider='bsa.single-phase-circuits'))
        for task in self.data['tasks'][3:]:
            row=copy.deepcopy(self.data['requirements'][0]);row.update(id='R-'+task['id'],task=task['id'])
            self.data['requirements'].append(row)
        self.save(self.plan,self.data)

    def baseline(self):
        execute(self.plan,self.root/'baseline')
        self.assertTrue(verify(self.root/'baseline')['integrity_pass'])
        core.checkpoint(self.root/'baseline',self.root/'checkpoint')

    def change_first(self):
        self.f.source.write_text('Synthetic airflow source changed.',encoding='utf-8')
        self.f.data['sources'][0]['source']=reference(self.f.source)
        self.save(self.f.manifest,self.f.data)

    def impact(self):return core.impact(self.root/'checkpoint')['tasks']

    def test_source_change_is_local_and_all_review_gates_remain(self):
        self.baseline();self.change_first();tasks=self.impact()
        for name in ('library','lookup','review'):self.assertTrue(tasks[name]['invalidated'])
        for name in ('other_library','other_query'):self.assertFalse(tasks[name]['invalidated'])
        self.assertTrue(tasks['independent']['reuse_eligible'])
        self.assertEqual(tasks['library']['input_ownership'],'verified_knowledge_closure')
        self.assertFalse(tasks['other_library']['reuse_eligible'])
        self.assertFalse(read_json(self.root/'baseline/workflow.json')['design_accepted'])

    def test_electrical_source_change_does_not_invalidate_knowledge(self):
        self.baseline();project=read_json(self.root/'electrical.json');project['devices'][0]['electrical_kw']*=1.25
        self.save(self.root/'electrical.json',project)
        request=read_json(self.root/'electrical-request.json');request['sources']['project']['sha256']=digest(self.root/'electrical.json')
        self.save(self.root/'electrical-request.json',request)
        tasks=self.impact();self.assertTrue(tasks['independent']['invalidated'])
        for name in ('library','lookup','other_library','other_query'):self.assertFalse(tasks[name]['invalidated'])

    def test_runtime_and_recipe_changes_keep_scope_and_global_requirements(self):
        self.baseline()
        from bsa.knowledge import index
        actual=index.runtime();changed={**actual,'sqlite':'different'}
        with patch.object(index,'runtime',return_value=changed):
            tasks=self.impact()
        for name in ('library','lookup','other_library','other_query'):self.assertIn('knowledge_runtime_changed',tasks[name]['reasons'])
        self.assertTrue(tasks['independent']['reuse_eligible'])
        self.data['tasks'][1]['query']['text']='different';self.save(self.plan,self.data)
        tasks=self.impact();self.assertTrue(tasks['lookup']['invalidated']);self.assertFalse(tasks['library']['invalidated'])
        self.assertFalse(tasks['other_query']['invalidated']);self.assertTrue(tasks['independent']['reuse_eligible'])
        self.data['requirements'][0]['acceptance']='Changed review criteria';self.save(self.plan,self.data)
        self.assertTrue(all(t['invalidated'] for t in self.impact().values()))

    def test_coherently_rehashed_ownership_cannot_hide_dropped_or_substituted_sources(self):
        self.baseline();path=self.root/'baseline/workflow.json';original=read_json(path)
        for mode in ('drop','substitute','runtime'):
            report=copy.deepcopy(original)
            if mode=='drop':report['knowledge_input_ownership']['tasks']['library'].remove(str(self.f.source))
            elif mode=='substitute':report['knowledge_input_ownership']['tasks']['library']=report['knowledge_input_ownership']['tasks']['other_library']
            else:report['knowledge_input_ownership']['runtime']['sqlite']='forged'
            self.save(path,report)
            checked=verify(self.root/'baseline');self.assertFalse(checked['integrity_pass'],mode)
        self.save(path,original)

    def test_saved_index_queries_capture_manifest_database_and_request_pins(self):
        build(self.f.manifest,self.root/'saved-index')
        task=self.data['tasks'][1];del task['depends_on'];task['index_receipt']='saved-index/receipt.json'
        self.save(self.plan,self.data);self.baseline()
        paths=read_json(self.root/'baseline/workflow.json')['knowledge_input_ownership']['tasks']['lookup']
        for name in ('receipt.json','request.json','index.sqlite'):self.assertIn(str(self.root/'saved-index'/name),paths)
        self.change_first();tasks=self.impact()
        self.assertTrue(tasks['lookup']['invalidated'])
        # An invalid current saved index invalidates the whole current plan conservatively.
        self.assertIn('current_plan_invalid',tasks['independent']['reasons'])

    def test_legacy_checkpoint_has_no_invented_ownership(self):
        self.baseline()
        # Reconstruct the older workflow shape and checkpoint while sources still match.
        report=read_json(self.root/'baseline/workflow.json');del report['knowledge_input_ownership']
        self.save(self.root/'baseline/workflow.json',report)
        self.assertTrue(verify(self.root/'baseline')['integrity_pass'])
        core.checkpoint(self.root/'baseline',self.root/'legacy-checkpoint')
        self.change_first();tasks=core.impact(self.root/'legacy-checkpoint')['tasks']
        self.assertEqual(tasks['other_library']['input_ownership'],'conservative_workflow_inputs')
        self.assertTrue(tasks['other_library']['invalidated'])

    def test_domain_methods_are_local_but_shared_orchestration_stays_global(self):
        self.baseline();actual=core.file_hash
        for path,global_gate in [(ROOT/'src/bsa/knowledge/sources.py',False),(ROOT/'src/bsa/workflow.py',True)]:
            def changed(p):return '0'*64 if Path(p)==path else actual(p)
            with patch.object(core,'file_hash',side_effect=changed):tasks=self.impact()
            self.assertTrue(tasks['library']['invalidated'])
            self.assertTrue(tasks['other_library']['invalidated'])
            self.assertEqual(tasks['independent']['invalidated'],global_gate)

    def test_project_input_ownership_includes_nested_original_producer_evidence(self):
        from tests import test_engineering_data_workflow
        f=test_engineering_data_workflow.CommonDataWorkflowTests();f.setUp();self.addCleanup(f.doCleanups)
        f.plan_data['tasks'][1]['include_inputs']=True;f.save(f.plan,f.plan_data)
        execute(f.plan,f.root/'producer')
        (self.root/'context.json').write_bytes((f.root/'context.json').read_bytes())
        self.data['project_context']='context.json'
        request=read_json(self.root/'electrical-request.json');request.update(project_id=f.context['project_id'],scenario_id=f.context['scenario_id'])
        self.save(self.root/'electrical-request.json',request)
        manifest=copy.deepcopy(self.f.data);manifest['project_context']=reference(self.root/'context.json')
        manifest['sources'][0].update(kind='project_inputs',role='project_input',source=reference(f.root/'producer/data/inputs.json'))
        self.save(self.root/'inputs-manifest.json',manifest)
        task=dict(id='input_library',kind='knowledge_index',manifest='inputs-manifest.json')
        self.data['tasks'].append(task)
        row=copy.deepcopy(self.data['requirements'][0]);row.update(id='R-inputs',task=task['id']);self.data['requirements'].append(row)
        self.save(self.plan,self.data);self.baseline()
        paths=read_json(self.root/'baseline/workflow.json')['knowledge_input_ownership']['tasks']['input_library']
        for path in (f.project,f.root/'producer/analysis/result.json',f.root/'producer/data/receipt.json',f.root/'producer/data/inputs.json'):
            self.assertIn(str(path),paths)
        self.assertIn(str(ROOT/'src/bsa/providers/electrical_circuits.py'),paths)

    def test_immutable_git_sources_remain_bound_to_manifest_and_reference_reader(self):
        from bsa import reference_library
        row=reference_library.catalogue(kind='docs',query='ENGINEERING_INPUTS.md',limit=1)['references'][0]
        revision=reference_library.git('rev-parse','HEAD').decode().strip()
        original=reference_library.read(revision,row['id'])
        self.f.data['sources'][0].update(kind='git_reference',role='agent_guide',
            source=dict(revision=revision,reference_id=row['id'],sha256=original['sha256']))
        self.save(self.f.manifest,self.f.data);self.baseline()
        paths=read_json(self.root/'baseline/workflow.json')['knowledge_input_ownership']['tasks']['library']
        self.assertIn(str(self.f.manifest),paths)
        self.assertIn(str(ROOT/'src/bsa/reference_library.py'),paths)
        self.f.data['sources'][0]['conditions']='Changed declared applicability; still not authenticated'
        self.save(self.f.manifest,self.f.data)
        tasks=self.impact();self.assertTrue(tasks['library']['invalidated'])
        self.assertFalse(tasks['other_library']['invalidated']);self.assertTrue(tasks['independent']['reuse_eligible'])

    def test_rehashed_checkpoint_copy_cannot_forge_old_ownership(self):
        self.baseline();path=self.root/'checkpoint/workflow.json';report=read_json(path)
        report['knowledge_input_ownership']['tasks']['library']=report['knowledge_input_ownership']['tasks']['other_library']
        self.save(path,report)
        receipt=read_json(self.root/'checkpoint/receipt.json');receipt['artifacts']['workflow.json']=digest(path)
        self.save(self.root/'checkpoint/receipt.json',receipt)
        with self.assertRaisesRegex(ValueError,'archive differs from original record'):self.impact()
