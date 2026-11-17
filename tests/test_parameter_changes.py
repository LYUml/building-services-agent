import copy
import shutil
import unittest

from bsa.changes import core
from bsa.changes.parameters import paths
from bsa.engineering_data.inputs import project_parameters
from bsa.module_contract import read_json
from bsa.source_refs import file_hash
from tests import test_changes


class ParameterChangeTests(unittest.TestCase):
    def setUp(self):
        fixture=test_changes.ChangeImpactTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.f=fixture

    def save_project(self,project):
        self.f.save(self.f.fixture.project,project)
        self.f.fixture.request_data['sources']['project']['sha256']=file_hash(self.f.fixture.project)
        self.f.save(self.f.fixture.request,self.f.fixture.request_data)

    def compared(self,**options):
        return core.impact(self.f.checkpoint,**options)['tasks']['analysis']['parameter_changes']

    def test_actual_input_change_has_stable_owner_original_units_and_si_delta(self):
        self.f.change_primary();report=self.compared()
        self.assertEqual(report['status'],'compared')
        self.assertEqual(report['total_changes'],3)
        self.assertFalse(report['current_producer_executed'])
        for row in report['changes']:
            self.assertEqual(row['name'],'electrical_kw')
            self.assertEqual(row['before']['id'],row['after']['id'])
            self.assertEqual(row['before']['quantity']['unit'],'kW electrical')
            self.assertEqual(row['after']['quantity']['classification'],'declared')
            self.assertAlmostEqual(row['delta_si'],10)
            self.assertEqual(row['delta_si_unit'],'W electrical')
        self.assertEqual(core.impact(self.f.checkpoint)['tasks']['independent']['parameter_changes']['total_changes'],0)

    def test_pagination_is_explicit_and_does_not_hide_total_changes(self):
        self.f.change_primary()
        first=self.compared(parameter_limit=1);second=self.compared(parameter_offset=1,parameter_limit=1)
        self.assertEqual(first['total_changes'],3);self.assertTrue(first['has_more'])
        self.assertNotEqual(first['changes'][0]['id'],second['changes'][0]['id'])
        with self.assertRaises(ValueError):core.impact(self.f.checkpoint,parameter_limit=101)

    def test_reordering_keeps_identity_and_only_moves_source_locations(self):
        project=read_json(self.f.fixture.project);project['devices'].reverse();self.save_project(project)
        report=self.compared();self.assertTrue(report['changes'])
        self.assertTrue(all(row['kinds']==['location_changed'] and row['delta_si']==0 for row in report['changes']))

    def test_added_and_removed_entities_are_not_mixed_as_numeric_deltas(self):
        project=read_json(self.f.fixture.project);project['devices'][-1]['id']='L4';self.save_project(project)
        report=self.compared();self.assertEqual(report['total_changes'],8)
        self.assertTrue(all(row['kinds'] in (['added'],['removed']) and row['delta_si'] is None for row in report['changes']))

    def test_long_source_note_is_omitted_explicitly_without_changing_raw_sources(self):
        project=read_json(self.f.fixture.project);text='Long synthetic source note. '*200
        project['sources']['demo']=text;self.save_project(project)
        report=self.compared();row=report['changes'][0]
        self.assertIn('source_note_changed',row['kinds'])
        self.assertIsNone(row['after']['source_text']);self.assertTrue(row['after']['source_text_omitted'])
        self.assertEqual(row['after']['source_text_length'],len(text))
        self.assertEqual(read_json(self.f.fixture.project)['sources']['demo'],text)

    def test_rehashed_source_archive_cannot_forge_original_values(self):
        name=paths('analysis')[1];path=self.f.checkpoint/name
        data=read_json(path);data['devices'][0]['electrical_kw']*=2;self.f.save(path,data)
        receipt=read_json(self.f.checkpoint/'receipt.json');receipt['artifacts'][name]=file_hash(path)
        self.f.save(self.f.checkpoint/'receipt.json',receipt)
        with self.assertRaisesRegex(ValueError,'original primary source'):core.impact(self.f.checkpoint)

    def test_legacy_checkpoint_is_readable_without_invented_parameter_history(self):
        legacy=self.f.root/'legacy';shutil.copytree(self.f.checkpoint,legacy)
        receipt=read_json(legacy/'receipt.json');receipt['schema']='bsa.change-checkpoint/1'
        for task in ('analysis','independent'):
            for name in paths(task):
                (legacy/name).unlink();del receipt['artifacts'][name]
        self.f.save(legacy/'receipt.json',receipt)
        self.assertEqual(core.impact(legacy)['tasks']['analysis']['parameter_changes']['status'],'not_recorded')

    def test_other_project_identity_and_wrong_thermal_units_are_not_compared(self):
        self.f.fixture.request_data['project_id']='8c6bfc32-8935-4d06-9d04-20d7809414c3'
        self.f.save(self.f.fixture.request,self.f.fixture.request_data)
        self.assertEqual(self.compared()['status'],'not_comparable')
        from bsa.air_load import UNITS
        values=dict(area=1,cooling_allowance=100,sensible_fraction=.9,density=1.2,specific_heat=1006,temperature_difference=10)
        loads={k:dict(value=v,unit=UNITS[k],classification='assumed',source='Synthetic unit control') for k,v in values.items()}
        loads['cooling_allowance']['unit']='kVA'
        with self.assertRaises(ValueError):project_parameters(dict(load_inputs=loads),'synthetic','bsa.air-allocation/1')
