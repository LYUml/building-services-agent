import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.hvac_project import ROOT, create, load, run


class HVACProjectTests(unittest.TestCase):
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
