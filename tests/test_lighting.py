import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.lighting import validate,ies_metadata,run
from bsa.engine import ProjectError
from bsa.workflow import execute
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/lighting/project.json'


class LightingTests(unittest.TestCase):
    def test_launch_failure_is_recorded_without_success_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p,path=self.fixture(root)
            binaries=root/'bin';binaries.mkdir()
            suffix='.exe' if os.name=='nt' else ''
            for name in ('ies2rad','xform','oconv','rtrace'):
                (binaries/(name+suffix)).write_bytes(b'not executed')
            with patch('bsa.lighting.subprocess.run',side_effect=OSError('launch blocked')):
                with self.assertRaisesRegex(ProjectError,'could not start'):
                    run(path,root/'out',binaries)
            calls=json.loads((root/'out/engine-calls.json').read_text())
            self.assertEqual(calls[-1]['launch_error'],'launch blocked')
            self.assertIsNone(calls[-1]['returncode'])
            self.assertFalse((root/'out/lighting.json').exists())

    def test_photometry_is_not_inferred_from_watts(self):
        meta=ies_metadata(EXAMPLE.parent/'synthetic-1000cd.ies')
        self.assertEqual(meta['input_watts'],40)
        self.assertEqual(meta['photometric_type'],'C')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.ies'
            text=(EXAMPLE.parent/'synthetic-1000cd.ies').read_text()
            path.write_text(text.replace('TILT=NONE','TILT=INCLUDE'))
            with self.assertRaises(ProjectError):ies_metadata(path)
            path.write_text(text+'\n!arbitrary scene command\n')
            with self.assertRaises(ProjectError):ies_metadata(path)

    def test_invalid_spatial_and_photometry_inputs_rejected(self):
        base=json.loads(EXAMPLE.read_text())
        for mutate in (lambda p:p['luminaires'][0].update(maintenance_factor=2),
                       lambda p:p['luminaires'][0].update(tilt_deg=45),
                       lambda p:p['room'].update(wall_reflectance=1.1),
                       lambda p:p['luminaires'][0].update(ies='../outside.ies'),
                       lambda p:p['sensors'][0].update(position_m=[0,0,0]),
                       lambda p:p['sensors'][0].update(source='unknown')):
            p=copy.deepcopy(base);mutate(p)
            with self.assertRaises(ProjectError):validate(p,EXAMPLE.parent)

    def fixture(self,root):
        p=json.loads(EXAMPLE.read_text())
        shutil.copyfile(EXAMPLE.parent/'synthetic-1000cd.ies',root/'synthetic-1000cd.ies')
        path=root/'project.json';path.write_text(json.dumps(p))
        return p,path

    def test_workflow_hashes_ies_and_marks_missing_engine_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p,path=self.fixture(root)
            brief=root/'brief.md';brief.write_text('Compute the supplied IES sensor illuminance.\n')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='light',kind='lighting',project='project.json')],
                requirements=[dict(id='R1',passage='P001',quote='Compute the supplied IES sensor illuminance.',task='light',acceptance='IES-backed point calculation')])
            plan_path=root/'plan.json';plan_path.write_text(json.dumps(plan))
            r=execute(plan_path,root/'run')
            self.assertEqual(r['tasks']['light']['status'],'pending')
            self.assertIn(str((root/'synthetic-1000cd.ies').resolve()),r['inputs'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_RADIANCE_BIN'),'requires local Radiance binaries')
    def test_real_engine_matches_analytical_lux_and_maintenance_scaling(self):
        root=ROOT/'runs';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            root=Path(folder);p,path=self.fixture(root)
            p['room'].update(wall_reflectance=0,floor_reflectance=0,ceiling_reflectance=0)
            p['luminaires'][0].update(position_m=[3,2,2.7],maintenance_factor=1)
            p['sensors']=[dict(id='AXIS',position_m=[3,2,0.7],source='demo'),dict(id='OFF',position_m=[4,2,0.7],source='demo')]
            p['simulation'].update(ambient_bounces=1,ambient_divisions=64,verification_bounces=2,verification_divisions=128)
            path.write_text(json.dumps(p))
            baseline=run(path,root/'baseline',Path(os.environ['BSA_TEST_RADIANCE_BIN']))
            self.assertAlmostEqual(baseline['sensors'][0]['direct_lux'],1000/2**2,delta=0.3)
            self.assertAlmostEqual(baseline['sensors'][1]['direct_lux'],1000*2/(5**1.5),delta=0.3)
            self.assertTrue(baseline['inputs_unchanged'])
            self.assertIn('RADIANCE',baseline['engine_version'])
            self.assertFalse(baseline['design_accepted'])
            p['luminaires'][0]['maintenance_factor']=0.5
            p['targets']['average_lux']=10000
            path.write_text(json.dumps(p))
            changed=run(path,root/'changed',Path(os.environ['BSA_TEST_RADIANCE_BIN']))
            self.assertAlmostEqual(changed['sensors'][0]['direct_lux'],baseline['sensors'][0]['direct_lux']/2,delta=0.1)
            self.assertFalse(changed['calculated_checks_pass'])
            self.assertEqual(changed['photometry']['L1']['input_watts'],40)


if __name__=='__main__':unittest.main()
