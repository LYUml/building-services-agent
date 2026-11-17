import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.engineering_data.model import entity_id, validate
from bsa.engineering_data.module_bridge import export, project_result, verify
from bsa.engineering_data.quantities import quantity
from bsa.module_contract import read_json
from bsa.modules import run

ROOT = Path(__file__).resolve().parents[1]


class EngineeringDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root/'project.json'
        self.project.write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
        self.request = self.root/'request.json'
        self.request.write_text(json.dumps(dict(schema='bsa.module-request/1',
            project_id='synthetic-common-data-control', scenario_id='baseline',
            capability='analysis.electrical.single-phase-circuits',
            coordinate_frame=dict(id='electrical-metres', kind='source-world-si', length_unit='m', georeferenced=False),
            sources=dict(project=dict(path='project.json', sha256=digest(self.project))))), encoding='utf-8')

    def producer(self, name='electrical', disabled=False):
        run(self.request, 'bsa.single-phase-circuits', self.root/name, disabled=disabled)
        return self.root/name/'result.json'

    def rehash(self, out):
        receipt = read_json(out/'receipt.json')
        receipt['artifacts'] = {n: digest(out/n) for n in receipt['artifacts']}
        (out/'receipt.json').write_text(json.dumps(receipt), encoding='utf-8')

    def test_real_electrical_engine_to_common_report_preserves_semantics(self):
        source = self.producer()
        original = source.read_bytes()
        out = self.root/'common'
        export(source, out)
        checked = verify(out)
        data = read_json(out/'model.json')
        circuit = next(e for e in data['entities'] if e['kind'] == 'electrical_circuit')
        q = circuit['quantities']['connected_electrical_kw']
        self.assertEqual(q['dimension'], 'electrical_real_power')
        self.assertEqual(q['si_value'], q['value']*1000)
        self.assertEqual(q['si_unit'], 'W electrical')
        self.assertFalse(data['design_accepted'])
        self.assertEqual(data['source_acceptance']['status'], 'pending')
        self.assertTrue(checked['integrity_pass'])
        self.assertGreater(checked['entity_count'], 1)
        self.assertIn(circuit['source_id'], (out/'summary.html').read_text())
        self.assertEqual(source.read_bytes(), original)

    def test_second_domain_uses_same_report_and_preserves_airflow(self):
        from bsa.air_load import UNITS
        boundary = self.root/'boundary.json'
        boundary.write_text(json.dumps(dict(type='Polygon', coordinates=[[[0, 0], [8, 0], [8, 6], [0, 6], [0, 0]]])), encoding='utf-8')
        values = dict(area=48, cooling_allowance=80, sensible_fraction=.85,
                      density=1.2, specific_heat=1006, temperature_difference=10)
        project = self.root/'air-project.json'
        project.write_text(json.dumps(dict(boundary=boundary.name, boundary_sha256=digest(boundary),
            geometry_basis='Synthetic common-data control in metres',
            terminals=[dict(id='T'+str(i), center_m=xy) for i, xy in enumerate([[2, 1.5], [6, 1.5], [2, 4.5], [6, 4.5]], 1)],
            load_inputs={k: dict(value=v, unit=UNITS[k], source='Synthetic control', classification='assumed') for k, v in values.items()},
            turndown=.5)), encoding='utf-8')
        request = read_json(self.request)
        request.update(capability='analysis.air.classified-allocation')
        request['sources']['project'] = dict(path=os.path.relpath(project, self.root), sha256=digest(project))
        self.request.write_text(json.dumps(request), encoding='utf-8')
        result = run(self.request, 'bsa.classified-air-allocation', self.root/'air')
        export(self.root/'air/result.json', self.root/'air-common')
        data = read_json(self.root/'air-common/model.json')
        system = next(e for e in data['entities'] if e['kind'] == 'air_system')
        terminals = [e for e in data['entities'] if e['kind'] == 'air_terminal']
        self.assertAlmostEqual(sum(e['quantities']['maximum_flow']['si_value'] for e in terminals),
                               system['quantities']['supply_flow']['si_value'])
        self.assertEqual(system['quantities']['total_cooling']['dimension'], 'thermal_power')
        self.assertFalse(data['source_flags']['room_sensible_load_verified'])
        self.assertEqual(len(terminals), len(result['payload']['terminals']))
        self.assertTrue(verify(self.root/'air-common')['integrity_pass'])

    def test_id_stability_across_scenario_and_input_change(self):
        first = project_result(self.producer())
        project = read_json(self.project)
        project['devices'][0]['electrical_kw'] *= 1.1
        self.project.write_text(json.dumps(project), encoding='utf-8')
        request = read_json(self.request)
        request['scenario_id'] = 'revised'
        request['sources']['project']['sha256'] = digest(self.project)
        self.request.write_text(json.dumps(request), encoding='utf-8')
        second = project_result(self.producer('revised'))
        self.assertEqual([e['id'] for e in first['entities']], [e['id'] for e in second['entities']])
        self.assertNotEqual(first['entities'], second['entities'])
        self.assertNotEqual(entity_id('another-project', 'electrical_circuit', 'C1'),
                            entity_id('this-project', 'electrical_circuit', 'C1'))

    def test_ambiguous_nonfinite_and_semantic_unit_forgery_reject(self):
        for value, unit in [(1, 'kW'), (True, 'A'), (float('nan'), 'A'), (float('inf'), 'VA')]:
            with self.subTest(value=value, unit=unit), self.assertRaises(ValueError):
                quantity(value, unit, '/payload/test')
        data = project_result(self.producer())
        q = next(e for e in data['entities'] if e['kind'] == 'electrical_circuit')['quantities']['connected_electrical_kw']
        q['dimension'] = 'thermal_power'
        with self.assertRaisesRegex(ValueError, 'dimension'):
            validate(data)

    def test_rehashed_quantity_and_report_forgery_reject(self):
        source = self.producer()
        for name in ('quantity', 'html', 'flags'):
            out = self.root/name
            export(source, out)
            if name == 'html':
                (out/'summary.html').write_text('PASS: everything accepted', encoding='utf-8')
            else:
                data = read_json(out/'model.json')
                if name == 'flags':
                    data['source_flags']['pending'] = []
                else:
                    q = next(e for e in data['entities'] if e['kind'] == 'electrical_circuit')['quantities']['design_current_a']
                    q['value'] += 10
                    q['si_value'] += 10
                (out/'model.json').write_text(json.dumps(data), encoding='utf-8')
            self.rehash(out)
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify(out)

    def test_duplicate_identity_broken_relation_and_source_escape_reject(self):
        original = project_result(self.producer())
        for change in ('duplicate', 'edge', 'path'):
            data = copy.deepcopy(original)
            if change == 'duplicate':
                data['entities'].append(copy.deepcopy(data['entities'][0]))
            elif change == 'edge':
                data['relationships'][0]['to'] = 'bsa:'+'0'*32
            else:
                data['source_result']['path'] = '../outside.json'
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(data)

    def test_disabled_and_numerically_failed_are_not_fabricated_success(self):
        source = self.producer('disabled', disabled=True)
        with self.assertRaisesRegex(ValueError, 'Completed verified'):
            export(source, self.root/'no-output')
        self.assertFalse((self.root/'no-output').exists())
        project = read_json(self.project)
        project['circuits'][0]['breaker_a'] = .01
        self.project.write_text(json.dumps(project), encoding='utf-8')
        request = read_json(self.request)
        request['sources']['project']['sha256'] = digest(self.project)
        self.request.write_text(json.dumps(request), encoding='utf-8')
        failed = project_result(self.producer('failed'))
        self.assertEqual(failed['source_flags']['status'], 'fail')
        self.assertFalse(failed['design_accepted'])

    def test_explicit_external_workspace_and_fresh_output_guards(self):
        source = self.producer()
        out = self.root/'valid'
        export(source, out)
        with self.assertRaises(ValueError):
            export(source, out)
        with self.assertRaises(ValueError):
            export(source, ROOT/'src/bsa/invalid-data-output')
        with self.assertRaises(ValueError):
            export(source, ROOT.parent/'polyu_bse3124/invalid-data-output')
        with patch.dict(os.environ, {'BSA_PROJECT_ROOT': str(self.root)}):
            export(source, self.root/'selected')
            data = read_json(self.root/'selected/model.json')
            self.assertEqual(data['source_result']['workspace'], 'project')
            self.assertTrue(verify(self.root/'selected')['integrity_pass'])

    def test_common_model_import_does_not_load_optional_engines(self):
        code = "import sys; import bsa.engineering_data.model; assert not ({'numpy','ifcopenshell','fluids','shapely','jsonschema'} & set(sys.modules))"
        subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True)

    def test_installed_cli_exports_and_rejects_changed_saved_report(self):
        source = self.producer()
        out = self.root/'cli'
        command = [sys.executable, '-X', 'utf8', '-m', 'bsa.cli', 'engineering-data']
        result = subprocess.run(command+['export', str(source), '--out', str(out)],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['design_accepted'])
        result = subprocess.run(command+['verify', str(out)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['integrity_pass'])
        (out/'summary.html').write_text('Changed', encoding='utf-8')
        result = subprocess.run(command+['verify', str(out)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('changed', result.stderr)
