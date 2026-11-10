import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.workflow import execute, verify


class DrainageWorkflowTests(unittest.TestCase):
    def test_execution_blocking_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def save(name, value):
                path = root / name
                path.write_text(json.dumps(value), encoding='utf-8')
                return path
            official = root / 'synthetic-source.txt'
            official.write_text('Synthetic test bytes, not official legal evidence')
            sha = digest(official)
            spec = dict(scope=dict(building_storeys=21, stack_scope='building',
                                  edition_basis='Synthetic edition', works_basis='Synthetic works', evidence='Synthetic survey'),
                        fixtures=[dict(id='WC1', floor_offset=1, connected_to_stack=False,
                                       separate_to_manhole=True, source='Synthetic connection')],
                        inventory_complete=True, inventory_source='Synthetic full inventory',
                        references={official.name: sha}, official_reference=official.name)
            save('connections.json', spec)
            save('du.json', dict(fixtures=[dict(id='A', count=1, DU_per_fixture=2, source='Synthetic', classification='assumed')],
                                 frequency_factor=dict(value=.5, source='Synthetic', classification='assumed'),
                                 model_facts=dict(connected_inventory_verified=True, frequency_classification_verified=True),
                                 basis='Independent synthetic downstream gate probe, not inventory binding', references={official.name: sha}))
            brief = root / 'brief.txt'
            brief.write_text('Review drainage connections before downstream execution.\n')
            tasks = [dict(id='check', kind='drainage_connections', project='connections.json'),
                     dict(id='downstream', kind='discharge_demand', project='du.json', requires_pass=['check'])]
            plan = save('plan.json', dict(version=1, brief=brief.name, brief_sha256=digest(brief),
                        passage_dispositions={'P001': 'requirement'}, tasks=tasks,
                        requirements=[dict(id='R'+str(i), passage='P001', quote='Review drainage connections before downstream execution.',
                                           task=t['id'], acceptance='Scoped checks; complete engineering acceptance pending') for i,t in enumerate(tasks)]))
            # Replace only the expected official byte hash; production pin stays unchanged.
            with patch('bsa.drainage_connections.OFFICIAL_SHA256', sha):
                positive = execute(plan, root / 'positive')
                self.assertEqual(positive['tasks']['check']['status'], 'pass')
                self.assertEqual(positive['tasks']['downstream']['status'], 'pass')
                self.assertFalse(positive['design_accepted'])
                self.assertTrue(verify(root / 'positive')['integrity_pass'])
                for name, value, expected in [('unknown', None, 'pending'), ('bad', False, 'fail')]:
                    spec['fixtures'][0]['separate_to_manhole'] = value
                    save('connections.json', spec)
                    result = execute(plan, root / name)
                    self.assertEqual(result['tasks']['check']['status'], expected)
                    self.assertEqual(result['tasks']['downstream']['status'], 'pending')
                    self.assertFalse((root / name / 'downstream' / 'demand.json').exists())
                self.assertTrue(verify(root / 'bad')['integrity_pass'])
                official.write_text('Changed source')
                self.assertFalse(verify(root / 'bad')['integrity_pass'])

    def test_source_pin_is_not_optional(self):
        from bsa.drainage_connections import run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'fake.txt'
            source.write_text('Not official')
            project = root / 'project.json'
            project.write_text(json.dumps(dict(scope={}, fixtures=[], inventory_complete=True,
                inventory_source='Synthetic', references={source.name: digest(source)}, official_reference=source.name)))
            with self.assertRaisesRegex(ValueError, 'Pinned November 2023'):
                run(project, root / 'result.json')
            self.assertFalse((root / 'result.json').exists())
