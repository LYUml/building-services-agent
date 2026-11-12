import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from bsa.spatial_recognition_check import check

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('BSA_TEST_MOOSAS_TRANSFORM')=='1','Explicit pinned MOOSAS runtime trial required')
class MoosasTransformProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def execute(self,fixture,name,grid=None,*,catalogue=True,expected_code=0):
        output=self.root/name
        cmd=[sys.executable,'-X','utf8',str(ROOT/'scripts/probe_moosas_transform.py'),
            '--source',str(ROOT/'examples/moosas-transform'/fixture),'--upstream',str(ROOT/'tools/moosas-review'),
            '--deps',str(ROOT/'tools/moosas-exchange-deps'),'--out',str(output)]
        if catalogue:cmd+=['--empty-catalogue']
        if grid is not None:cmd+=['--point-grid-m',str(grid)]
        process=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=60)
        self.assertEqual(process.returncode,expected_code,process.stdout+process.stderr)
        result=json.loads((output/'probe.json').read_text())
        self.assertTrue(result['point_grid_restored'])
        if expected_code==0:self.assertTrue(result['saved_reload_matches'])
        self.assertFalse(result['simulation_executed']);self.assertFalse(result['design_accepted'])
        return result

    def test_finer_grid_preserves_rotated_and_narrow_boundaries_without_changing_targets(self):
        for fixture in ('rotated-room','narrow-notch','l-shaped-room'):
            r=self.execute(fixture+'.geo',fixture,1e-9)
            expected=json.loads((ROOT/f'examples/moosas-transform/{fixture}.expected.json').read_text())
            result=check(r['spaces'],expected['expected'],length_tolerance_m=expected['length_tolerance_m'],area_tolerance_m2=expected['area_tolerance_m2'])
            self.assertTrue(result['source_geometry_matches'])

    def test_finer_grid_preserves_closed_two_room_and_missing_wall_controls(self):
        for fixture,areas in [('closed-room.geo',[12]),('two-rooms.geo',[6,12]),('missing-wall.geo',[])]:
            r=self.execute(fixture,fixture,1e-9)
            self.assertEqual(sorted(s['area_m2'] for s in r['spaces']),areas)
            self.assertTrue(all(s['height_m']==3 and not s['is_open'] for s in r['spaces']))

    def test_default_grid_remains_default_and_rotated_fidelity_failure_remains_visible(self):
        r=self.execute('rotated-room.geo','default')
        self.assertEqual(r['point_grid_m'],.001)
        expected=json.loads((ROOT/'examples/moosas-transform/rotated-room.expected.json').read_text())
        result=check(r['spaces'],expected['expected'],length_tolerance_m=expected['length_tolerance_m'],area_tolerance_m2=expected['area_tolerance_m2'])
        self.assertFalse(result['source_geometry_matches'])

    def test_failing_catalogue_restores_grid_and_retains_failure(self):
        r=self.execute('closed-room.geo','failed-catalogue',1e-9,catalogue=False,expected_code=2)
        self.assertEqual(r['execution'],'failed')
        self.assertIn('schema/version',r['diagnostic']['message'])
