import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.engineering_data.context import create, load
from bsa.engineering_data.module_bridge import export, project_result, verify as verify_data
from bsa.module_contract import read_json
from bsa.modules import run
from bsa.workflow import execute, validate_plan, verify

ROOT = Path(__file__).resolve().parents[1]


class CommonDataWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root/'project.json'
        self.project.write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
        self.context = create('Synthetic project isolation control', 'baseline', self.root/'context.json')
        self.request = self.root/'request.json'
        self.request_data = dict(schema='bsa.module-request/1', project_id=self.context['project_id'],
            scenario_id=self.context['scenario_id'], capability='analysis.electrical.single-phase-circuits',
            coordinate_frame=dict(id='declared-electrical-metres', kind='source-world-si', length_unit='m', georeferenced=False),
            sources=dict(project=dict(path='project.json', sha256=digest(self.project))))
        self.save(self.request, self.request_data)
        text = 'Calculate the synthetic source and retain common data and independent engineering review.'
        (self.root/'brief.md').write_text(text, encoding='utf-8')
        tasks = [dict(id='analysis', kind='module_analysis', request='request.json', provider='bsa.single-phase-circuits'),
                 dict(id='data', kind='engineering_data', depends_on='analysis'),
                 dict(id='review', kind='manual', requires_pass=['data'], description='Engineering acceptance remains pending')]
        self.plan_data = dict(version=1, brief='brief.md', brief_sha256=digest(self.root/'brief.md'),
            project_context='context.json', passage_dispositions=dict(P001='requirement'), tasks=tasks,
            requirements=[dict(id='R'+str(i), passage='P001', quote=text, task=t['id'],
                               acceptance='Source correspondence and separate engineering review') for i, t in enumerate(tasks)])
        self.plan = self.root/'plan.json'
        self.save(self.plan, self.plan_data)

    def save(self, path, data):
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def test_source_bound_workflow_and_delivery_keep_all_requirements(self):
        out = self.root/'run'
        result = execute(self.plan, out)
        self.assertEqual([t['status'] for t in result['tasks'].values()], ['pass', 'pass', 'pending'])
        self.assertTrue(verify(out)['integrity_pass'])
        from bsa.delivery import context
        context(self.plan, out)
        model = read_json(out/'data/model.json')
        self.assertEqual(model['project_id'], self.context['project_id'])
        self.assertEqual({r['id'] for r in result['requirements']}, {'R0', 'R1', 'R2'})
        self.assertTrue(all(r['acceptance_status'] == 'pending review' for r in result['requirements']))
        self.assertFalse(result['design_accepted'])

    def test_two_projects_with_same_source_ids_are_isolated(self):
        execute(self.plan, self.root/'first')
        first = read_json(self.root/'first/data/model.json')
        next_context = create('Same friendly name is allowed', 'baseline', self.root/'another-context.json')
        self.request_data['project_id'] = next_context['project_id']
        self.save(self.request, self.request_data)
        self.plan_data['project_context'] = 'another-context.json'
        self.save(self.plan, self.plan_data)
        execute(self.plan, self.root/'second')
        second = read_json(self.root/'second/data/model.json')
        self.assertEqual([e['source_id'] for e in first['entities']], [e['source_id'] for e in second['entities']])
        self.assertFalse({e['id'] for e in first['entities']} & {e['id'] for e in second['entities']})

    def test_context_mismatch_and_replacement_fields_reject_before_execution(self):
        for mode in ('project', 'scenario', 'override', 'missing'):
            plan = copy.deepcopy(self.plan_data)
            request = copy.deepcopy(self.request_data)
            if mode == 'project':
                request['project_id'] = 'another-project'
            elif mode == 'scenario':
                request['scenario_id'] = 'another-scenario'
            elif mode == 'override':
                plan['tasks'][1]['source_result'] = 'unrelated/result.json'
            else:
                del plan['project_context']
            self.save(self.plan, plan)
            self.save(self.request, request)
            with self.subTest(mode=mode), patch('bsa.modules.run') as engine:
                with self.assertRaises(ValueError):
                    execute(self.plan, self.root/('rejected-'+mode))
                engine.assert_not_called()
                self.assertFalse((self.root/('rejected-'+mode)).exists())

    def test_valid_export_from_another_producer_cannot_be_substituted(self):
        out = self.root/'run'
        execute(self.plan, out)
        run(self.request, 'bsa.single-phase-circuits', self.root/'another-producer')
        export(self.root/'another-producer/result.json', self.root/'foreign-data')
        for name in ('model.json', 'summary.html', 'receipt.json'):
            (out/'data'/name).write_bytes((self.root/'foreign-data'/name).read_bytes())
        self.assertTrue(verify_data(out/'data')['integrity_pass'])
        report = read_json(out/'workflow.json')
        for name in ('model.json', 'summary.html', 'receipt.json'):
            report['artifact_hashes']['data/'+name] = digest(out/'data'/name)
        self.save(out/'workflow.json', report)
        checked = verify(out)
        self.assertFalse(checked['integrity_pass'])
        self.assertTrue(any('declared workflow producer' in issue for issue in checked['issues']))

    def test_disabled_provider_blocks_export_and_retains_review(self):
        out = self.root/'disabled'
        result = execute(self.plan, out, disabled_module_providers=['bsa.single-phase-circuits'])
        self.assertEqual(result['tasks']['analysis']['status'], 'pending')
        self.assertEqual(result['tasks']['data']['status'], 'pending')
        self.assertFalse((out/'data').exists())
        self.assertTrue(verify(out)['integrity_pass'])

    def test_changed_declared_request_cannot_hide_behind_valid_module_replay(self):
        out = self.root/'run'
        execute(self.plan, out)
        another = self.root/'another-request.json'
        another.write_bytes(self.request.read_bytes())
        run(another, 'bsa.single-phase-circuits', self.root/'foreign-producer')
        for item in (self.root/'foreign-producer').rglob('*'):
            if item.is_file():
                target = out/'analysis'/item.relative_to(self.root/'foreign-producer')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(item.read_bytes())
        export(out/'analysis/result.json', self.root/'foreign-view')
        for name in ('model.json', 'summary.html', 'receipt.json'):
            (out/'data'/name).write_bytes((self.root/'foreign-view'/name).read_bytes())
        report = read_json(out/'workflow.json')
        for name in report['artifact_hashes']:
            report['artifact_hashes'][name] = digest(out/name)
        self.save(out/'workflow.json', report)
        checked = verify(out)
        self.assertFalse(checked['integrity_pass'])
        self.assertTrue(any('declared source task' in issue for issue in checked['issues']))

    def test_context_and_method_pins_cannot_be_omitted(self):
        out = self.root/'run'
        execute(self.plan, out)
        report = read_json(out/'workflow.json')
        del report['inputs'][str((self.root/'context.json').resolve())]
        self.save(out/'workflow.json', report)
        checked = verify(out)
        self.assertFalse(checked['integrity_pass'])
        self.assertTrue(any('lost context or method' in issue for issue in checked['issues']))

    def test_failure_blocks_data_but_independent_branch_runs(self):
        baseline = self.root/'independent-project.json'
        baseline.write_bytes(self.project.read_bytes())
        request = copy.deepcopy(self.request_data)
        request['sources']['project'] = dict(path=baseline.name, sha256=digest(baseline))
        self.save(self.root/'independent-request.json', request)
        task = dict(id='independent', kind='module_analysis', request='independent-request.json', provider='bsa.single-phase-circuits')
        self.plan_data['tasks'].append(task)
        self.plan_data['requirements'].append(dict(self.plan_data['requirements'][0], id='R3', task='independent'))
        project = read_json(self.project)
        project['circuits'][0]['breaker_a'] = .01
        self.save(self.project, project)
        self.request_data['sources']['project']['sha256'] = digest(self.project)
        self.save(self.request, self.request_data)
        self.save(self.plan, self.plan_data)
        result = execute(self.plan, self.root/'failed')
        self.assertEqual(result['tasks']['analysis']['status'], 'fail')
        self.assertEqual(result['tasks']['data']['status'], 'pending')
        self.assertEqual(result['tasks']['independent']['status'], 'pass')
        self.assertTrue(verify(self.root/'failed')['integrity_pass'])

    def test_air_module_uses_same_context_and_common_task_without_network_solver(self):
        from bsa.air_load import UNITS
        boundary = self.root/'boundary.json'
        self.save(boundary, dict(type='Polygon', coordinates=[[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]))
        values = dict(area=16, cooling_allowance=80, sensible_fraction=.85, density=1.2,
                      specific_heat=1006, temperature_difference=10)
        self.save(self.project, dict(boundary=boundary.name, boundary_sha256=digest(boundary),
            geometry_basis='Synthetic SI control', terminals=[dict(id='T1', center_m=[1, 2]), dict(id='T2', center_m=[3, 2])],
            load_inputs={k: dict(value=v, unit=UNITS[k], source='Synthetic control', classification='assumed') for k, v in values.items()}, turndown=.4))
        self.request_data.update(capability='analysis.air.classified-allocation')
        self.request_data['sources']['project']['sha256'] = digest(self.project)
        self.save(self.request, self.request_data)
        self.plan_data['tasks'][0]['provider'] = 'bsa.classified-air-allocation'
        self.save(self.plan, self.plan_data)
        result = execute(self.plan, self.root/'air')
        self.assertEqual(result['tasks']['data']['status'], 'pass')
        self.assertTrue(verify(self.root/'air')['integrity_pass'])
        self.assertEqual(read_json(self.root/'air/data/model.json')['payload_schema'], 'bsa.air-allocation/1')

    def test_project_context_cli_is_persisted_and_never_overwritten(self):
        out = self.root/'cli-context.json'
        command = [sys.executable, '-X', 'utf8', '-m', 'bsa.cli', 'engineering-data',
                   'context', '--name', 'Test project', '--scenario', 'baseline', '--out', str(out)]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        original = out.read_bytes()
        self.assertNotEqual(load(out)['project_id'], self.context['project_id'])
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(out.read_bytes(), original)

    def test_legacy_placeholder_and_context_drift_are_explicit(self):
        self.request_data['project_id'] = 'workflow-allocation'
        self.save(self.request, self.request_data)
        run(self.request, 'bsa.single-phase-circuits', self.root/'legacy')
        with self.assertRaisesRegex(ValueError, 'Legacy placeholder'):
            project_result(self.root/'legacy/result.json')
        self.request_data['project_id'] = self.context['project_id']
        self.save(self.request, self.request_data)
        execute(self.plan, self.root/'run')
        context = read_json(self.root/'context.json')
        context['name'] = 'Edited after execution'
        self.save(self.root/'context.json', context)
        self.assertFalse(verify(self.root/'run')['integrity_pass'])
