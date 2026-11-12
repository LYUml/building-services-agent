import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from bsa.engineering_handoff import verify

ROOT=Path(__file__).resolve().parents[1]


class CoupledHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        execute=runpy.run_path(str(ROOT/'scripts/run_coupled_handoff_demo.py'))['execute']
        cls.positive=execute(cls.root/'positive')
        cls.negative=execute(cls.root/'negative',True)
        cls.no_engine=execute(cls.root/'no-engine',native=True)
        with patch('bsa.ifc_native.run') as native:
            cls.native_negative=execute(cls.root/'native-negative',True,native=True,autocad='not-started.exe')
        native.assert_not_called()

    def test_shared_identity_unit_bound_scenario_and_source_preservation(self):
        root=self.root/'positive';result=verify(root/'engineering-run')
        self.assertEqual(result['task_statuses'],dict(electrical='pass',water='pass',qa='pass',pump='pass',coupled='pass',**{'coupled-qa':'pass','drawing':'pass','review':'pending'}))
        self.assertEqual(len(result['original_requirement_ids']),7)
        report=json.loads((root/'engineering-run/workflow/coupled/pump-electrical.json').read_text())
        link=json.loads((root/'pump-electrical-link.json').read_text())
        self.assertEqual(report['record']['pump_guid'],link['pump_guid'])
        self.assertEqual(report['record']['source_port_guid'],link['source_port_guid'])
        self.assertEqual(report['record']['baseline_electrical_kw'],.75)
        self.assertEqual(report['saved_typed_properties'],dict(property_count=15,typed_values_pass=True,explicit_units_pass=True))
        self.assertTrue(report['existing_ifc_entities_unchanged'])
        self.assertTrue(report['baseline_hardware_retained'])
        self.assertFalse(report['design_accepted'])
        for name,transfer in self.positive['source_transfers'].items():
            self.assertEqual((root/name).read_bytes(),(root/transfer['archived']).read_bytes())

    def test_port_guid_cannot_substitute_for_pump_or_release_downstream(self):
        root=self.root/'negative';result=verify(root/'engineering-run')
        self.assertEqual(result['task_statuses']['coupled'],'fail')
        self.assertTrue(all(result['task_statuses'][name]=='pending' for name in ('coupled-qa','drawing','review')))
        self.assertEqual(result['recovery_schedule']['ready_tasks'],['coupled'])
        self.assertFalse((root/'engineering-run/workflow/coupled/model.ifc').exists())
        self.assertFalse((root/'engineering-run/workflow/drawing').exists())
        transfer=self.negative['source_transfers']['pump-electrical-link.json']
        self.assertNotEqual((root/'pump-electrical-link.json').read_bytes(),(root/transfer['archived']).read_bytes())
        self.assertEqual((root/transfer['archived']).read_bytes(),(ROOT/'examples/water-riser/pump-electrical-link.json').read_bytes())

    def test_native_scope_preserves_all_supplement_passages_without_fabricating_runtime(self):
        result=verify(self.root/'no-engine/engineering-run')
        self.assertEqual(len(result['original_requirement_ids']),9)
        self.assertEqual(result['task_statuses']['drawing'],'pass')
        self.assertEqual(result['task_statuses']['native'],'pending')
        self.assertEqual(result['task_statuses']['review'],'pending')
        self.assertEqual(result['recovery_schedule']['ready_tasks'],['native'])
        self.assertFalse((self.root/'no-engine/engineering-run/workflow/native').exists())

    def test_failed_identity_blocks_native_even_with_explicit_host_runtime(self):
        result=verify(self.root/'native-negative/engineering-run')
        self.assertEqual(result['task_statuses']['coupled'],'fail')
        self.assertEqual(result['task_statuses']['native'],'pending')
        self.assertFalse((self.root/'native-negative/engineering-run/workflow/native').exists())


if __name__=='__main__':unittest.main()
