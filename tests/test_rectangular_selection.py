import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.rectangular_design import run,selected_input
from bsa.workflow import execute,validate_plan
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'


class RectangularSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ('brief.md','undersized.json','catalogue.json','selected-plan.json'):(self.root/name).write_bytes((EX/name).read_bytes())

    def test_inherited_selected_input_is_freshly_solved(self):
        execute(self.root/'selected-plan.json',self.root/'run')
        d=diagnose(self.root/'selected-plan.json',self.root/'run')
        self.assertEqual([r['status'] for r in d['tasks']],['pass','pass','pending'])
        report=json.loads((self.root/'run/selected-check/network.json').read_text())
        self.assertEqual(report['input_sha256'],digest(self.root/'run/air/selected-network.json'))
        self.assertNotEqual(report['input_sha256'],digest(self.root/'undersized.json'))

    def test_replacement_project_rejected(self):
        path=self.root/'selected-plan.json';p=json.loads(path.read_text());p['tasks'][1]['project']='undersized.json';path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'replacement project'):validate_plan(path)

    def test_no_feasible_blocks_inherited_analysis(self):
        path=self.root/'catalogue.json';p=json.loads(path.read_text())
        for key in p['allowed_options']:p['allowed_options'][key]=['small']
        path.write_text(json.dumps(p));execute(self.root/'selected-plan.json',self.root/'run')
        d=diagnose(self.root/'selected-plan.json',self.root/'run')
        self.assertEqual([r['status'] for r in d['tasks']],['fail','pending','pending'])
        self.assertFalse((self.root/'run/selected-check').exists())

    def test_changed_selected_even_with_rewritten_artifact_hash_rejected(self):
        out=self.root/'producer';run(self.root/'undersized.json',self.root/'catalogue.json',out)
        path=out/'selected-network.json';p=json.loads(path.read_text());p['segments'][0]['width_m']+=.01;path.write_text(json.dumps(p))
        report=out/'design-comparison.json';r=json.loads(report.read_text());r['artifacts']['selected-network.json']=digest(path);report.write_text(json.dumps(r))
        with self.assertRaisesRegex(ProjectError,'source reconstruction'):selected_input(out,self.root/'undersized.json',self.root/'catalogue.json')

    def test_consumer_boundary_artifact_change_blocks_before_pressure_engine(self):
        from bsa.rectangular_design import selected_input as original
        def corrupt(producer,*args):
            path=Path(producer)/'selected-network.json';path.write_text('{}')
            return original(producer,*args)
        with patch('bsa.rectangular_design.selected_input',side_effect=corrupt):execute(self.root/'selected-plan.json',self.root/'run')
        self.assertFalse((self.root/'run/selected-check').exists())
