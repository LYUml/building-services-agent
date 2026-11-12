import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.hvac_project import ROOT, create, load, run


class HVACProjectTests(unittest.TestCase):
    def test_requirements_inventory_is_pinned_and_changed_inventory_rejects(self):
        from bsa.project_start import start
        brief = self.root/'raw-brief.md'
        brief.write_text('Calculate ventilation and produce editable drawings.')
        result = start(brief, self.root/'intake')
        plan = self.root/'intake'/result['effective_plan']
        inventory = self.root/'intake'/result['requirements_module']['result']
        create(plan, self.configuration, requirements_result=inventory)
        files, _, pins = load(self.configuration)
        self.assertEqual(files['requirements_result'], inventory.resolve())
        self.assertIn(inventory.resolve(), pins)
        from bsa.hvac_package import run as package_run
        other_plan = plan.with_name('same-bytes-other-plan.json')
        other_plan.write_bytes(plan.read_bytes())
        denied_output = self.root/'wrong-plan-package'
        with self.assertRaisesRegex(ValueError, 'exact execution plan'):
            package_run(other_plan, denied_output, font='not-needed', requirements_result=inventory)
        self.assertFalse(denied_output.exists())
        def bound_package(plan_arg, output, **kwargs):
            self.assertEqual(kwargs['requirements_result'], inventory.resolve())
            output.mkdir()
            (output/'package.json').write_text('{}')
            return {'status': 'review_required'}
        with patch('bsa.hvac_project.hvac_package.run', side_effect=bound_package):
            receipt = run(self.configuration, self.root/'bound-package', font='host font')
        self.assertIn(str(inventory.resolve()), receipt['input_hashes'])
        with patch('bsa.hvac_project.hvac_package.run') as package:
            inventory.write_bytes(inventory.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                run(self.configuration, self.root/'changed-inventory', font='host font')
            package.assert_not_called()

    def test_external_configuration_requires_same_host_workspace_on_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            with patch.dict(os.environ, {'BSA_PROJECT_ROOT': str(root)}):
                plan = runpy.run_path(str(ROOT/'examples/hvac-package/build_inputs.py'))['build'](root/'inputs')
                configuration = root/'project.json'
                create(plan, configuration)
                files, _, pins = load(configuration)
                self.assertEqual(files['plan'], plan)
                self.assertIn(plan.parent/'source.dxf', pins)
                self.assertIn(ROOT/'src/bsa/workspace.py', pins)
                with self.assertRaisesRegex(ValueError, 'host-selected'):
                    create(plan, root.parent/'unselected-bsa-project.json')
            with patch.dict(os.environ, {'BSA_PROJECT_ROOT': ''}):
                with self.assertRaisesRegex(ValueError, 'host-selected'):
                    load(configuration)
                with self.assertRaisesRegex(ValueError, 'host-selected'):
                    create(plan, self.root/'external-denied.json')
            with patch.dict(os.environ, {'BSA_PROJECT_ROOT': str(root)}):
                (plan.parent/'source.dxf').write_bytes(b'changed source')
                with self.assertRaisesRegex(ValueError, 'source changed'):
                    load(configuration)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = runpy.run_path(str(ROOT/'examples/hvac-package/build_inputs.py'))['build'](self.root/'inputs')
        self.configuration = self.root/'project.json'

    def create(self):
        return create(self.plan, self.configuration, terminal_review=self.plan.parent/'review.json',
                      junction_review_native_task='native', system_paths_native_task='native')

    def test_source_inventory_settings_handoff_and_receipt(self):
        data = self.create()
        files, selectors, pins = load(self.configuration)
        self.assertIn(self.plan.parent/'source.dxf', pins)
        self.assertIn(self.plan.parent/'brief.md', pins)
        self.assertIn(self.plan.parent/'catalogue.json', pins)
        self.assertIn(ROOT/'src/bsa/hvac_project.py',pins)
        self.assertIn(ROOT/'src/bsa/air_allocation.py',pins)
        self.assertIn(ROOT/'scripts/water_saved_graph.py',pins)
        self.assertIn(ROOT/'contracts/modules/request-v1.json',pins)
        self.assertEqual(selectors['system_paths_native_task'], 'native')
        output = self.root/'package'
        def package(plan, out, **kwargs):
            self.assertEqual(plan, self.plan)
            self.assertEqual(kwargs['terminal_review'], self.plan.parent/'review.json')
            self.assertEqual(kwargs['junction_review_native_task'], 'native')
            self.assertEqual(kwargs['system_paths_native_task'], 'native')
            self.assertEqual(kwargs['autocad'], 'Explicit host runtime')
            out.mkdir(); result = dict(status='review_required', design_accepted=False)
            (out/'package.json').write_text(json.dumps(result))
            return result
        # Plumbing only; mocked execution does not claim a native CAD/PDF run.
        with patch('bsa.hvac_project.hvac_package.run', side_effect=package):
            receipt = run(self.configuration, output, font='Explicit host font', autocad='Explicit host runtime')
        self.assertEqual(receipt['package_sha256'], digest(output/'package.json'))
        self.assertEqual(receipt['configuration_sha256'], digest(self.configuration))
        self.assertFalse(receipt['design_accepted'])
        with self.assertRaisesRegex(ValueError, 'existing files'): self.create()
        omitted = self.root/'omitted.json'
        create(self.plan, omitted)
        self.assertTrue(all(v is None for v in load(omitted)[1].values()))

    def test_changed_source_and_incomplete_inventory_reject_before_execution(self):
        original = self.create()
        for relative in ('source.dxf', 'review.json', 'catalogue.json'):
            source = self.plan.parent/relative; raw = source.read_bytes()
            source.write_bytes(raw+b' ')
            with patch('bsa.hvac_project.hvac_package.run') as package:
                with self.assertRaisesRegex(ValueError, 'source changed'):
                    run(self.configuration, self.root/'changed', font='host font')
                package.assert_not_called()
            source.write_bytes(raw)
        changed = json.loads(json.dumps(original))
        key = next(k for k in changed['input_hashes'] if k.endswith('source.dxf'))
        changed['input_hashes'].pop(key)
        self.configuration.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'Complete current'): load(self.configuration)

    def test_method_change_and_added_method_require_a_new_configuration(self):
        method=self.root/'worker.py';method.write_text('original method')
        with patch('bsa.hvac_project.method_inputs',return_value={method}):
            self.create();method.write_text('changed method')
            with patch('bsa.hvac_project.hvac_package.run') as package:
                with self.assertRaisesRegex(ValueError,'source changed'):run(self.configuration,self.root/'changed',font='host font')
                package.assert_not_called()
            method.write_text('original method');extra=self.root/'added.py';extra.write_text('new method')
            with patch('bsa.hvac_project.method_inputs',return_value={method,extra}):
                with self.assertRaisesRegex(ValueError,'Complete current'):load(self.configuration)

    def test_method_addition_during_execution_keeps_receipt_absent(self):
        method=self.root/'worker.py';method.write_text('original method');methods={method}
        with patch('bsa.hvac_project.method_inputs',side_effect=lambda:set(methods)):
            self.create()
            def package(plan,out,**kwargs):
                out.mkdir();(out/'package.json').write_text('{}');extra=self.root/'new.py';extra.write_text('added during execution');methods.add(extra)
                return dict(status='review_required')
            output=self.root/'changed-set'
            with patch('bsa.hvac_project.hvac_package.run',side_effect=package):
                with self.assertRaisesRegex(ValueError,'inventory changed during'):run(self.configuration,output,font='host font')
            self.assertFalse((output/'project-run.json').exists())

    def test_runtime_fields_escape_invalid_selector_and_overwrite_reject(self):
        original = self.create()
        for changed in (dict(original, autocad='from untrusted data'), dict(original, command='anything')):
            self.configuration.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'no engine or command'): load(self.configuration)
        changed = json.loads(json.dumps(original)); changed['files']['plan'] = str(self.plan)
        self.configuration.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'relative'): load(self.configuration)
        changed = json.loads(json.dumps(original)); changed['files']['plan'] = '../../../outside.json'
        self.configuration.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'Repository-local'): load(self.configuration)
        with self.assertRaisesRegex(ValueError, 'declared native'):
            create(self.plan, self.root/'invalid.json', system_paths_native_task='engineering')
        self.assertFalse((self.root/'invalid.json').exists())
        self.configuration.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, 'separate'):
            run(self.configuration, self.root, font='host font')

    def test_mutation_during_execution_keeps_completion_receipt_absent(self):
        self.create()
        for target in (self.configuration, self.plan.parent/'source.dxf'):
            raw = target.read_bytes(); output = self.root/('mutate-'+target.suffix[1:])
            def package(plan, out, **kwargs):
                out.mkdir(); (out/'package.json').write_text('{}')
                target.write_bytes(raw+b' ')
                return dict(status='review_required')
            with patch('bsa.hvac_project.hvac_package.run', side_effect=package):
                with self.assertRaisesRegex(ValueError, 'changed during'):
                    run(self.configuration, output, font='host font')
            self.assertFalse((output/'project-run.json').exists())
            target.write_bytes(raw)

    def test_adpi_document_pin_and_source_replacement_reject(self):
        source = self.root/'criterion.txt'; source.write_text('Synthetic source pin control only')
        settings = self.root/'adpi.json'
        settings.write_text(json.dumps(dict(source=source.name, source_sha256=digest(source),
            criterion=dict(source='Synthetic source pin control',room_load_range_W_m2=[35,160],ratio_range=[1,3.4]),
            room_load_W_m2=None,facts={k:None for k in ('room_load_verified','product_category_verified','lengths_verified','installation_verified','edition_selected')})))
        create(self.plan, self.configuration, adpi_settings=settings)
        self.assertIn(source, load(self.configuration)[2])
        source.write_text('Changed source')
        with self.assertRaisesRegex(ValueError, 'source changed'): load(self.configuration)
        with self.assertRaisesRegex(ValueError, 'ADPI source hash'):
            create(self.plan, self.root/'bad-adpi.json', adpi_settings=settings)

    def test_adpi_fact_evidence_enters_complete_project_inventory(self):
        source=self.root/'criterion.txt';source.write_text('Synthetic criterion')
        extra=self.root/'category.txt';extra.write_text('Synthetic category evidence')
        settings=self.root/'settings.json'
        settings.write_text(json.dumps(dict(source=source.name,source_sha256=digest(source),criterion={},facts={},room_load_W_m2=None,
            fact_evidence=dict(product_category_verified=[dict(source=extra.name,sha256=digest(extra),locator='Synthetic paragraph',note='Source inventory control only')]))))
        create(self.plan,self.configuration,adpi_settings=settings)
        self.assertIn(extra,load(self.configuration)[2])
        extra.write_text('Changed evidence')
        with patch('bsa.hvac_project.hvac_package.run') as package:
            with self.assertRaisesRegex(ValueError,'source changed'):
                run(self.configuration,self.root/'changed',font='host font')
            package.assert_not_called()

    def test_terminal_performance_inventory_and_omitted_source_reject(self):
        source=self.root/'manufacturer.txt';source.write_text('Synthetic performance source')
        catalogue=self.root/'performance.json';catalogue.write_text('{}')
        settings=self.root/'performance-settings.json'
        settings.write_text(json.dumps(dict(source=source.name,source_sha256=digest(source),catalogue=catalogue.name,
            catalogue_sha256=digest(catalogue),conditions='Synthetic source inventory only')))
        original=create(self.plan,self.configuration,terminal_performance=settings)
        files,_,pins=load(self.configuration)
        self.assertEqual(files['terminal_performance'],settings)
        self.assertIn(source,pins);self.assertIn(catalogue,pins)
        key=next(p for p in original['input_hashes'] if p.endswith('manufacturer.txt'))
        original['input_hashes'].pop(key);self.configuration.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError,'Complete current'):load(self.configuration)
        source.write_text('Changed manufacturer source')
        with self.assertRaisesRegex(ValueError,'source hash'):
            create(self.plan,self.root/'changed.json',terminal_performance=settings)
