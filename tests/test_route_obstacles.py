import json
from pathlib import Path
import tempfile
import unittest

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.route_obstacles import contract,run

ROOT=Path(__file__).resolve().parents[1]


class RouteObstacleTests(unittest.TestCase):
    def setUp(self):
        self.routing=json.loads((ROOT/'examples/route-search/route-input.json').read_text())
        self.heights=json.loads((ROOT/'examples/route-search/obstacle-heights.json').read_text())

    def test_exact_sourced_height_coverage_required(self):
        for heights in ({},{'COLUMN':{'min_z_m':0,'max_z_m':2}}, {'COLUMN':dict(min_z_m=2,max_z_m=1,source='test')},dict(self.heights,EXTRA=self.heights['COLUMN'])):
            with self.subTest(heights=heights),self.assertRaises(ProjectError):contract(self.routing,heights)

    def test_native_append_preserves_source_and_checks_closed_box(self):
        from bsa.bim import run as author
        from bsa.route_model import compile_route
        routing=dict(self.routing,obstacles=[])
        settings=json.loads((ROOT/'examples/route-search/model-settings.json').read_text())
        network=json.loads((ROOT/'examples/route-search/network.json').read_text())
        _,model,_,_=compile_route(routing,settings,network)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);p=root/'model.json';p.write_text(json.dumps(model))
            author(p,root/'source');ifc=root/'source/model.ifc';before=digest(ifc)
            result=run(ifc,ROOT/'examples/route-search/route-input.json',ROOT/'examples/route-search/obstacle-heights.json',root/'appended')
            self.assertEqual(digest(ifc),before)
            self.assertTrue(result['original_entities_unchanged'])
            self.assertAlmostEqual(result['obstacles'][0]['saved_volume_m3'],.8)
            self.assertFalse(result['design_accepted'])
            with self.assertRaisesRegex(ProjectError,'already exists'):
                run(root/'appended/model.ifc',ROOT/'examples/route-search/route-input.json',ROOT/'examples/route-search/obstacle-heights.json',root/'duplicate')
