import json
from pathlib import Path
import runpy
import tempfile
import unittest
from bsa.cli import digest
from bsa.delivery import context
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]


class WaterRuleDrawingGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        cache=self.root/'cache';cache.mkdir();build=runpy.run_path(str(ROOT/'examples/modular/build_water_rules_inputs.py'))['build']
        self.plan=build(self.root/'inputs',cache,drawings=True);folder=self.plan.parent
        source=folder/'sources/emsd-bec-2024.pdf';source.write_bytes(b'SYNTHETIC DRAWING GATE TEST SOURCE')
        pack=folder/'source/pack.json';p=json.loads(pack.read_text());p['sources']['emsd_bec_2024']['sha256']=digest(source);pack.write_text(json.dumps(p))

    def test_exact_model_views_execute_and_missing_native_host_stays_pending(self):
        out=self.root/'run';w=execute(self.plan,out)
        self.assertEqual(w['tasks']['views']['status'],'pass');self.assertEqual(w['tasks']['native']['status'],'pending')
        views=json.loads((out/'views/views.json').read_text());self.assertEqual(len(views['views']),2)
        self.assertEqual(len(views['settings']['labels']),4);self.assertFalse((out/'native/drawing-set.pdf').exists())
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)

    def test_known_rule_failure_blocks_both_drawing_stages(self):
        basis=self.plan.parent/'source/regulatory-bases.json';p=json.loads(basis.read_text())
        for row in p['pipes'].values():row['water_pipe'].update(flow_mode=dict(value='variable',source='negative control'),pump_control=dict(value='single_fixed_speed',source='negative control'))
        basis.write_text(json.dumps(p));out=self.root/'failed';w=execute(self.plan,out)
        self.assertEqual(w['tasks']['rules']['status'],'fail')
        for name in ('views','native'):
            self.assertEqual(w['tasks'][name]['status'],'pending');self.assertFalse((out/name).exists())
        self.assertTrue(verify(out)['integrity_pass']);context(self.plan,out)
