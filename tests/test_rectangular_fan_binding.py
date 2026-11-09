import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ifcopenshell
from bsa.rectangular_binding import run as bind
from bsa.rectangular_fan_binding import run
from bsa.engine import ProjectError
from bsa.workflow import execute,validate_plan
from bsa.cli import digest
ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'

class RectangularFanBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.base=cls.root/'producer'
        bind(EX/'elbow-chain-project.json',EX/'elbow-chain-model.json',EX/'elbow-chain-binding.json',cls.base)

    def invoke(self,**changes):
        kwargs=dict(project=self.base/'network-input.json',model=EX/'elbow-chain-model.json',binding=EX/'elbow-chain-binding.json',ifc=self.base/'bim/model.ifc',analysis=self.base/'analysis/network.json',curve=EX/'fan-curve.json',out=self.root/self._testMethodName)
        kwargs.update(changes);return run(**kwargs)

    def test_curved_native_chain_to_saved_operating_rerun(self):
        r=self.invoke()
        self.assertTrue(r['geometry_bound']);self.assertTrue(r['native_path_correspondence_pass'])
        self.assertAlmostEqual(r['operating_point']['flow_m3_s'],.7236704506,delta=1e-8)
        self.assertTrue(r['selected_rerun_pass']);self.assertFalse(r['design_accepted'])

    def test_changed_saved_bend_rejected_before_solver(self):
        path=self.root/'changed.ifc';m=ifcopenshell.open(str(self.base/'bim/model.ifc'))
        bend=m.by_type('IfcDuctFitting')[0]
        body=next(r for r in bend.Representation.Representations if r.RepresentationIdentifier=='Body').Items[0]
        body.Angle=1.
        m.write(str(path))
        with patch('bsa.rectangular_fan_binding.solve') as solver:
            with self.assertRaises(ProjectError):self.invoke(ifc=path)
            solver.assert_not_called()

    def test_changed_numerical_geometry_even_with_updated_study_hash_rejected(self):
        p=json.loads((self.base/'network-input.json').read_text());p['segments'][0]['length_m']-=.1
        path=self.root/'fake-project.json';path.write_text(json.dumps(p))
        study=json.loads((self.base/'analysis/network.json').read_text());study['input_sha256']=digest(path)
        report=self.root/'fake-study.json';report.write_text(json.dumps(study))
        with self.assertRaisesRegex(ProjectError,'geometry derivation'):self.invoke(project=path,analysis=report)

    def test_replacement_inputs_reject(self):
        import shutil
        root=self.root/'plans';root.mkdir()
        for p in EX.glob('*.json'):shutil.copyfile(p,root/p.name)
        shutil.copyfile(EX/'brief.md',root/'brief.md')
        path=root/'elbow-fan-plan.json';p=json.loads(path.read_text());p['tasks'][1]['project']='fan-project.json';path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'replacement project'):validate_plan(path)

    def test_upstream_pressure_failure_stops_fan(self):
        import shutil
        root=self.root/'low';root.mkdir()
        for p in EX.glob('*.json'):shutil.copyfile(p,root/p.name)
        shutil.copyfile(EX/'brief.md',root/'brief.md')
        p=json.loads((root/'elbow-chain-project.json').read_text());p['supply']['total_pressure_pa']=1;(root/'elbow-chain-project.json').write_text(json.dumps(p))
        r=execute(root/'elbow-fan-plan.json',root/'run')
        self.assertEqual(r['tasks']['air']['status'],'fail');self.assertEqual(r['tasks']['fan']['status'],'pending')
        self.assertFalse((root/'run/fan').exists())
