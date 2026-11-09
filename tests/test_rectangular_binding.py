import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.rectangular_binding import run
from bsa.network_binding import _prepare
from bsa.engine import ProjectError
from bsa.workflow import execute
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'


class RectangularBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.p=json.loads((EX/'binding-project.json').read_text());self.m=json.loads((EX/'straight-wall.json').read_text());self.b=json.loads((EX/'binding.json').read_text())

    def test_derived_dimensions_and_actual_native_pressure_analysis(self):
        r=run(EX/'binding-project.json',EX/'straight-wall.json',EX/'binding.json',self.root/'run')
        n=json.loads((self.root/'run/network-input.json').read_text());s=n['segments'][0]
        self.assertEqual((s['width_m'],s['height_m'],s['length_m']),(.5,.3,2))
        self.assertTrue(r['saved_ifc_geometry_match']);self.assertTrue(r['calculated_checks_pass']);self.assertFalse(r['design_accepted'])

    def test_duplicate_geometry_and_unknown_route_rejected(self):
        for key in ('length_m','width_m','height_m','diameter_m'):
            p=json.loads(json.dumps(self.p));p['segments'][0][key]=.5
            with self.assertRaises(ProjectError):_prepare(p,self.m,self.b,rectangular=True)
        self.b['segments']['MAIN']=['missing']
        with self.assertRaises(ProjectError):_prepare(self.p,self.m,self.b,rectangular=True)

    def test_changed_saved_profile_stops_before_pressure_analysis(self):
        from bsa.bim import run as author
        import ifcopenshell
        def changed(*args):
            r=author(*args);path=Path(args[1])/'model.ifc';model=ifcopenshell.open(str(path))
            model.by_type('IfcDuctSegment')[0].Representation.Representations[0].Items[0].SweptArea.XDim+=.01
            model.write(str(path));return r
        with patch('bsa.bim.run',side_effect=changed),patch('bsa.rectangular_network.run') as analysis:
            with self.assertRaisesRegex(ProjectError,'dimensions differ'):run(EX/'binding-project.json',EX/'straight-wall.json',EX/'binding.json',self.root/'run')
            analysis.assert_not_called()

    def test_workflow_positive_and_pressure_failure_keep_review_gate(self):
        for name in ('brief.md','binding-plan.json','binding.json','binding-project.json','straight-wall.json'):(self.root/name).write_bytes((EX/name).read_bytes())
        for label,pressure in (('positive',300),('low',1)):
            path=self.root/'binding-project.json';p=json.loads(path.read_text());p['supply']['total_pressure_pa']=pressure;path.write_text(json.dumps(p))
            execute(self.root/'binding-plan.json',self.root/label)
            rows=diagnose(self.root/'binding-plan.json',self.root/label)['tasks']
            self.assertEqual([r['status'] for r in rows],['pass' if label=='positive' else 'fail','pending'])
            if label=='low':self.assertEqual(rows[1]['blocked_by'],['air'])
