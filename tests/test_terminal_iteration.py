"""Dispatch controls only; actual source/model execution is recorded separately."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.terminal_iteration import run

ROOT=Path(__file__).resolve().parents[1]

class TerminalIterationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.plan=self.root/'plan.json';self.plan.write_text('{}');self.policy=self.root/'policy.json';self.policy.write_text('{}');self.geometry=self.root/'geometry.json';self.geometry.write_text('{}')
        self.original=self.root/'original';(self.original/'performance').mkdir(parents=True);(self.original/'workflow.json').write_text('{}');(self.original/'performance/terminal-performance.json').write_text('{}')
        self.target=self.root/'target.json';self.out=self.root/'iteration';self.source=dict(tasks=[dict(id='performance',kind='spatial_terminal_performance'),dict(id='body',kind='spatial_terminal_ifc',depends_on='performance')],requirements=[dict(id='R1',task='body')],unresolved_inputs=[])
        self.context=patch('bsa.terminal_iteration.delivery.context',return_value=(self.source,dict(inputs={},artifact_hashes={}),dict(integrity_pass=True)));self.context.start();self.addCleanup(self.context.stop)
    def invoke(self,**kwargs):return run(self.plan,self.original,'performance',self.policy,self.target,self.out,**kwargs)
    def test_infeasible_search_never_releases_plan_or_execution(self):
        studied=dict(proposal=dict(status='no_feasible_candidate'))
        with patch('bsa.terminal_iteration.search.run',return_value=studied),patch('bsa.terminal_iteration.search.verify'),patch('bsa.terminal_iteration.candidate_plan.run') as plan,patch('bsa.terminal_iteration.workflow.execute') as execute:
            result=self.invoke(geometry_policy=self.geometry)
        self.assertEqual(result['status'],'no_feasible_candidate');plan.assert_not_called();execute.assert_not_called();self.assertFalse(result['design_accepted']);self.assertTrue(result['original_inputs_unchanged'])
    def test_missing_geometry_policy_never_infers_physical_templates(self):
        with patch('bsa.terminal_iteration.search.run',return_value=dict(proposal=dict(status='candidate_available'))),patch('bsa.terminal_iteration.search.verify'),patch('bsa.terminal_iteration.candidate_plan.run') as plan:
            result=self.invoke()
        self.assertEqual(result['status'],'needs_geometry_policy');plan.assert_not_called();self.assertEqual(result['original_requirements'],self.source['requirements'])
    def test_disabled_inventory_stops_before_workflow(self):
        with patch('bsa.terminal_iteration.search.run',return_value=dict(proposal=dict(status='candidate_available'))),patch('bsa.terminal_iteration.search.verify'),patch('bsa.terminal_iteration.candidate_plan.run',side_effect=lambda *args:self.target.write_text('{}')),patch('bsa.terminal_iteration.modules.run',return_value=dict(execution=dict(status='unavailable'))) as inventory,patch('bsa.terminal_iteration.workflow.execute') as execute:
            result=self.invoke(geometry_policy=self.geometry,execute_options=dict(disabled_module_providers=['bsa.source-requirements']))
        self.assertEqual(result['status'],'requirements_unavailable');self.assertTrue(inventory.call_args.kwargs['disabled']);execute.assert_not_called()
    def test_unknown_host_commands_reject_before_output(self):
        with self.assertRaises(ValueError):self.invoke(execute_options={'command':'untrusted'})
        self.assertFalse(self.out.exists())
    def test_stale_source_context_rejects_before_search(self):
        with patch('bsa.terminal_iteration.delivery.context',return_value=(self.source,{},dict(integrity_pass=False))),patch('bsa.terminal_iteration.search.run') as search:
            with self.assertRaises(ValueError):self.invoke()
        search.assert_not_called();self.assertFalse(self.out.exists())

    def test_invalid_stage_release_rejects_without_engine_execution(self):
        from bsa.terminal_iteration import stage_order
        for stages in [dict(workflow='executed'),dict(search='no_feasible_candidate',plan='materialized_verified'),dict(plan='materialized_verified',requirements='completed'),dict(search='candidate_available',plan='materialized_verified',requirements='unavailable',workflow='executed')]:
            with self.subTest(stages=stages),self.assertRaises(ValueError):stage_order(stages)
        stage_order(dict(search='candidate_available',plan='materialized_verified',requirements='completed',workflow='executed',diagnosis='source_verified'))
    def test_otherwise_valid_foreign_search_cannot_replace_declared_source(self):
        from bsa.terminal_iteration import search_link
        original=self.original/'performance/terminal-performance.json'
        search_link(dict(original=str(original),policy=str(self.policy)),original,self.policy)
        with self.assertRaisesRegex(ValueError,'replaced declared'):
            search_link(dict(original=str(original),policy=str(self.geometry)),original,self.policy)
