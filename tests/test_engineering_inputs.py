import copy
import json
from pathlib import Path
import unittest

from bsa.cli import digest
from bsa.engineering_data.inputs import build, parameter_id, validate
from bsa.engineering_data.module_bridge import export, verify as verify_data
from bsa.module_contract import read_json
from bsa.modules import run
from bsa.workflow import execute, verify


class EngineeringInputsTests(unittest.TestCase):
    def setUp(self):
        from tests.test_engineering_data_workflow import CommonDataWorkflowTests
        self.f = CommonDataWorkflowTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root

    def producer(self):
        run(self.f.request, self.f.plan_data['tasks'][0]['provider'], self.root/'producer')
        return self.root/'producer/result.json'

    def air(self, cells=False):
        from bsa.air_load import UNITS
        boundary = self.root/'boundary.json'
        self.f.save(boundary, dict(type='Polygon', coordinates=[[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]))
        values = dict(area=16, cooling_allowance=80, sensible_fraction=.85,
                      density=1.2, specific_heat=1006, temperature_difference=10)
        project = dict(boundary=boundary.name, boundary_sha256=digest(boundary),
            geometry_basis='Synthetic explicit metre geometry; no actual survey',
            terminals=[dict(id='T1', center_m=[1, 2]), dict(id='T2', center_m=[3, 2])],
            load_inputs={k: dict(value=v, unit=UNITS[k], source='Synthetic source classification control',
                classification='secondary_transcription' if k=='cooling_allowance' else 'assumed') for k, v in values.items()}, turndown=.4)
        if cells:
            project.update(service_basis='Synthetic exact half-room partition', service_cells={
                'T1': dict(type='Polygon', coordinates=[[[0, 0], [2, 0], [2, 4], [0, 4], [0, 0]]]),
                'T2': dict(type='Polygon', coordinates=[[[2, 0], [4, 0], [4, 4], [2, 4], [2, 0]]])})
        self.f.save(self.f.project, project)
        self.f.request_data['capability'] = 'analysis.air.classified-allocation'
        self.f.request_data['sources']['project']['sha256'] = digest(self.f.project)
        self.f.save(self.f.request, self.f.request_data)
        self.f.plan_data['tasks'][0]['provider'] = 'bsa.classified-air-allocation'
        self.f.save(self.f.plan, self.f.plan_data)

    def rehash(self, out):
        receipt = read_json(out/'receipt.json')
        receipt['artifacts'] = {n: digest(out/n) for n in receipt['artifacts']}
        self.f.save(out/'receipt.json', receipt)

    def test_electrical_inputs_have_exact_source_ownership_without_derived_values(self):
        source = self.producer()
        before = self.f.project.read_bytes()
        data = build(source)
        self.assertEqual(len(data['parameters']), 20)
        self.assertEqual(data['coverage']['unmapped_numeric_pointers'], [])
        self.assertTrue(all(r['role']=='source_input' and r['review_required'] for r in data['parameters']))
        fields = {r['name'] for r in data['parameters']}
        self.assertNotIn('design_current_a', fields)
        self.assertNotIn('voltage_drop_v', fields)
        power = next(r for r in data['parameters'] if r['name']=='electrical_kw')
        self.assertEqual(power['quantity']['dimension'], 'electrical_real_power')
        self.assertEqual(power['quantity']['classification'], 'declared')
        self.assertIn('synthetic', power['source_text'].lower())
        self.assertTrue(power['source_note_pointer'].startswith('/sources/'))
        self.assertEqual(self.f.project.read_bytes(), before)
        self.assertFalse(data['source_assertions_authenticated'])

    def test_air_original_classification_and_ambiguous_source_unit_are_retained(self):
        self.air()
        data = build(self.producer())
        allowance = next(r for r in data['parameters'] if r['name']=='load.cooling_allowance')
        self.assertEqual(allowance['source_unit'], 'W/m2')
        self.assertEqual(allowance['quantity']['unit'], 'W thermal/m2')
        self.assertEqual(allowance['quantity']['classification'], 'secondary_transcription')
        self.assertEqual(allowance['quantity']['dimension'], 'thermal_load_density')
        self.assertEqual(len(data['parameters']), 11)
        self.assertFalse(any('supply_flow' in r['name'] for r in data['parameters']))

    def test_unmapped_geometry_is_explicit_and_not_silently_editable(self):
        self.air(cells=True)
        data = build(self.producer())
        self.assertEqual(data['coverage']['mapped_count'], 11)
        self.assertEqual(len(data['coverage']['unmapped_numeric_pointers']), 20)
        self.assertEqual(data['coverage']['numeric_leaf_count'], 31)
        self.assertTrue(all(p.startswith('/service_cells/') for p in data['coverage']['unmapped_numeric_pointers']))

    def test_parameter_ids_survive_source_array_reordering(self):
        first = build(self.producer())
        project = read_json(self.f.project)
        project['devices'].reverse()
        self.f.save(self.f.project, project)
        self.f.request_data['sources']['project']['sha256'] = digest(self.f.project)
        self.f.save(self.f.request, self.f.request_data)
        run(self.f.request, 'bsa.single-phase-circuits', self.root/'reordered')
        second = build(self.root/'reordered/result.json')
        self.assertEqual({r['id'] for r in first['parameters']}, {r['id'] for r in second['parameters']})
        a = next(r for r in first['parameters'] if r['name']=='electrical_kw')
        b = next(r for r in second['parameters'] if r['id']==a['id'])
        self.assertNotEqual(a['quantity']['source_pointer'], b['quantity']['source_pointer'])

    def test_old_bundle_and_new_source_catalogue_bundle_both_verify(self):
        source = self.producer()
        old, new = self.root/'old', self.root/'new'
        export(source, old)
        export(source, new, include_inputs=True)
        self.assertEqual(read_json(old/'receipt.json')['schema'], 'bsa.engineering-data-export/1')
        self.assertEqual(read_json(new/'receipt.json')['schema'], 'bsa.engineering-data-export/2')
        self.assertEqual(read_json(old/'model.json'), read_json(new/'model.json'))
        self.assertTrue(verify_data(old)['integrity_pass'])
        self.assertEqual(verify_data(new)['input_parameter_count'], 20)
        self.assertIn('Source inputs: review required', (new/'summary.html').read_text())

    def test_coherently_rehashed_value_classification_or_owner_change_rejects(self):
        source = self.producer()
        for mode in ('value', 'classification', 'owner', 'source_unit'):
            out = self.root/mode
            export(source, out, include_inputs=True)
            data = read_json(out/'inputs.json')
            row = data['parameters'][0]
            if mode=='value':
                row['quantity']['value'] += 1
                row['quantity']['si_value'] += 1
            elif mode=='classification':
                row['quantity']['classification'] = 'measured'
            elif mode=='owner':
                row['entity_id'] = next(p['entity_id'] for p in data['parameters'] if p['entity_id'] != row['entity_id'])
                row['id'] = parameter_id(row['entity_id'], row['name'])
            else:
                row['source_unit'] = 'kW thermal'
            self.f.save(out/'inputs.json', data)
            self.rehash(out)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                verify_data(out)

    def test_new_workflow_requires_requested_catalogue_and_preserves_requirements(self):
        self.f.plan_data['tasks'][1]['include_inputs'] = True
        self.f.save(self.f.plan, self.f.plan_data)
        out = self.root/'workflow'
        result = execute(self.f.plan, out)
        self.assertEqual(result['tasks']['data']['status'], 'pass')
        self.assertTrue(verify(out)['integrity_pass'])
        self.assertEqual(len(result['requirements']), 3)
        self.assertTrue(all(r['acceptance_status']=='pending review' for r in result['requirements']))

    def test_source_change_and_invalid_parameter_identity_cannot_pass(self):
        source = self.producer()
        data = build(source)
        changed = copy.deepcopy(data)
        changed['parameters'].append(copy.deepcopy(changed['parameters'][0]))
        with self.assertRaises(ValueError):
            validate(changed)
        out = self.root/'new'
        export(source, out, include_inputs=True)
        project = read_json(self.f.project)
        project['supply_voltage_v'] += 1
        self.f.save(self.f.project, project)
        with self.assertRaises(ValueError):
            verify_data(out)

    def test_coherent_old_bundle_substitution_cannot_omit_requested_inputs(self):
        self.f.plan_data['tasks'][1]['include_inputs'] = True
        self.f.save(self.f.plan, self.f.plan_data)
        out = self.root/'workflow'
        execute(self.f.plan, out)
        export(out/'analysis/result.json', self.root/'old-format')
        for name in ('model.json', 'summary.html', 'receipt.json'):
            (out/'data'/name).write_bytes((self.root/'old-format'/name).read_bytes())
        (out/'data/inputs.json').unlink()  # Owned temporary test file only.
        self.assertTrue(verify_data(out/'data')['integrity_pass'])
        report = read_json(out/'workflow.json')
        del report['artifact_hashes']['data/inputs.json']
        for name in ('model.json', 'summary.html', 'receipt.json'):
            report['artifact_hashes']['data/'+name] = digest(out/'data'/name)
        self.f.save(out/'workflow.json', report)
        checked = verify(out)
        self.assertFalse(checked['integrity_pass'])
        self.assertTrue(any('catalogue selection differs' in issue for issue in checked['issues']))
