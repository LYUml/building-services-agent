import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1];PYTHON=ROOT/'tools/gis-runtime/Scripts/python.exe';CACHE=ROOT/'runs/chicago-footprints-v2'

@unittest.skipUnless(PYTHON.is_file() and (CACHE/'snapshot.json').is_file(),'requires pinned GIS runtime and official source snapshot')
class GISContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.driver=staticmethod(runpy.run_path(str(ROOT/'scripts/stage_chicago_footprints.py'))['run'])
        cls.result=cls.driver(cls.root/'positive',PYTHON,CACHE)

    def test_snapshot_replay_retains_ids_topology_metres_and_unknown_heights(self):
        r=self.result
        self.assertEqual(r['feature_count'],34);self.assertEqual(r['unknown_height_count'],34)
        self.assertEqual(r['source_time_period'],'Current as of August 2015')
        self.assertTrue(r['geometry_checks_pass']);self.assertFalse(r['site_selected']);self.assertFalse(r['three_dimensional_context_ready'])
        self.assertTrue(all(f['height_m'] is None for f in r['features']))
        self.assertEqual(r['reference_xy_m'],[0.,0.]);self.assertAlmostEqual(r['north_probe_xy_m'][0],0.)
        self.assertTrue(110<r['north_probe_xy_m'][1]<112)
        self.assertLess(r['maximum_roundtrip_error_deg'],1e-9)
        self.assertAlmostEqual(sum(f['projected_area_m2'] for f in r['features']),47083.46235370397,places=5)
        self.assertEqual(digest(self.root/'positive/footprints.png'),digest(CACHE/'footprints.png'))

    def test_changed_cached_source_or_different_query_cannot_be_reused(self):
        for mode in ('source','query'):
            cache=self.root/('cache-'+mode);shutil.copytree(CACHE,cache)
            if mode=='source':
                path=cache/'sources/features.json';path.write_bytes(path.read_bytes()+b' ')
            else:
                path=cache/'snapshot.json';row=json.loads(path.read_text(encoding='utf-8'));row['urls']['features.json']='different-query';path.write_text(json.dumps(row),encoding='utf-8')
            out=self.root/('reject-'+mode)
            with self.subTest(mode=mode),self.assertRaises(ProjectError):self.driver(out,PYTHON,cache)
            self.assertFalse((out/'local-footprints.json').exists())

    def test_feet_scaled_geometry_fails_independent_geodesic_area_check(self):
        import subprocess
        native=subprocess.run
        def scale(command,**kwargs):
            result=native(command,**kwargs);path=Path(command[-1]);row=json.loads(path.read_text(encoding='utf-8'))
            for f in row['features']:
                for polygon in f['geometry']['coordinates']:
                    for ring in polygon:
                        for point in ring:point[0]*=3.28084;point[1]*=3.28084
            path.write_text(json.dumps(row),encoding='utf-8');return result
        with patch('subprocess.run',side_effect=scale),self.assertRaisesRegex(ProjectError,'geometry/area/unknown height'):
            self.driver(self.root/'wrong-units',PYTHON,CACHE)
