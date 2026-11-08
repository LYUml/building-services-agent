import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from bsa.engine import ProjectError
from bsa.network_binding import prepare, reconcile, run
from bsa import circular_elbow as elbow

ROOT = Path(__file__).resolve().parents[1]
AVAILABLE = bool(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('fluids'))


@unittest.skipUnless(AVAILABLE, 'requires BIM and network dependencies')
class CircularElbowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = [json.loads((ROOT/'examples/circular-elbow'/name).read_text())
                      for name in ('network.json', 'project.json', 'binding.json')]
        cls.folder = tempfile.TemporaryDirectory()
        cls.out = Path(cls.folder.name)/'result'
        paths = [ROOT/'examples/circular-elbow'/name for name in ('network.json', 'project.json', 'binding.json')]
        cls.result = run(*paths, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_native_bore_and_independent_laminar_pressure(self):
        self.assertTrue(self.result['calculated_checks_pass'])
        self.assertFalse(self.result['design_accepted'])
        length = 3 + math.pi*.3/2
        segment = self.result['segments'][0]
        self.assertAlmostEqual(segment['length_m'], length)
        self.assertAlmostEqual(segment['minor_k'], .4)
        report = json.loads((self.out/'analysis/network.json').read_text())
        velocity = .0001/(math.pi*.08**2/4)
        expected = 128*.001*length*.0001/(math.pi*.08**4) + .4*998*velocity**2/2
        self.assertAlmostEqual(report['segments'][0]['dissipative_loss_pa'], expected, places=10)
        import ifcopenshell
        native = ifcopenshell.open(str(self.out/'bim/model.ifc'))
        obj = native.by_type('IfcPipeFitting')[0]
        arc, ends, radius = elbow.saved_arc_length(obj)
        self.assertAlmostEqual(arc, math.pi*.3/2)
        self.assertAlmostEqual(radius, .3)
        self.assertGreater(arc, math.dist(*ends))
        body = next(r for r in obj.Representation.Representations if r.RepresentationIdentifier == 'Body')
        self.assertEqual(body.RepresentationType, 'Tessellation')
        self.assertTrue(body.Items[0].Closed)

    def test_invalid_source_geometry_and_loss_basis(self):
        for mutate in (
            lambda d: d['properties'].update(CenterlineRadius_m=.04),
            lambda d: d.update(bend_axes=['+X', '-X']),
            lambda d: d['ports'][0]['offset_m'].__setitem__(0, .29),
            lambda d: d['properties'].update(LocalLossBasis='total fitting loss'),
            lambda d: d['properties'].pop('LocalLossCoefficient'),
        ):
            n, m, b = copy.deepcopy(self.inputs)
            mutate(m['devices'][1])
            with self.assertRaises(ProjectError):
                prepare(n, m, b)
        n, m, b = copy.deepcopy(self.inputs)
        n['segments'][0]['minor_k'] = .4
        with self.assertRaises(ProjectError):
            prepare(n, m, b)

        n, m, b = copy.deepcopy(self.inputs)
        b['segments']['MAIN'] = [{}]
        with self.assertRaises(ProjectError):
            prepare(n, m, b)

    def test_all_signed_cardinal_arc_frames(self):
        import numpy as np
        count = 0
        for first, u in elbow.AXES.items():
            for second, v in elbow.AXES.items():
                if sum(a*b for a, b in zip(u, v)):
                    continue
                d = copy.deepcopy(self.inputs[1]['devices'][1])
                u, v = np.asarray(u), np.asarray(v)
                normal = np.cross(u, v)
                centre = np.asarray([2., 2., 1.])
                low = centre + np.minimum(u*.35, 0) + np.minimum(v*.35, 0) - abs(normal)*.05
                high = centre + np.maximum(u*.35, 0) + np.maximum(v*.35, 0) + abs(normal)*.05
                d.update(bend_axes=[first, second], origin_m=low.tolist(), size_m=(high-low).tolist())
                for p, direction in zip(d['ports'], (u, v)):
                    p['offset_m'] = (centre+.3*direction-low).tolist()
                spec = elbow.specification(d)
                self.assertAlmostEqual(spec['length_m'], .3*math.pi/2)
                self.assertEqual(spec['normals']['in'], (-v).tolist())
                self.assertEqual(spec['normals']['out'], (-u).tolist())
                count += 1
        self.assertEqual(count, 24)

    def test_saved_axis_and_loss_tampering_rejected(self):
        import ifcopenshell
        import ifcopenshell.api as api
        import ifcopenshell.util.element as element
        for kind in ('axis', 'loss'):
            native = ifcopenshell.open(str(self.out/'bim/model.ifc'))
            obj = native.by_type('IfcPipeFitting')[0]
            if kind == 'axis':
                axis = next(r for r in obj.Representation.Representations if r.RepresentationIdentifier == 'Axis')
                points = [list(p) for p in axis.Items[0].Points.CoordList]
                points[1][0] += .01
                axis.Items[0].Points.CoordList = points
            else:
                pset = element.get_psets(obj)['BSA_DesignInputs']
                api.run('pset.edit_pset', native, pset=native.by_id(pset['id']), properties={'LocalLossCoefficient': .5})
            target = Path(self.folder.name)/(kind+'.ifc')
            native.write(str(target))
            with self.assertRaises(ProjectError):
                reconcile(target, self.out/'network-input.json', self.inputs[2], self.inputs[1])


if __name__ == '__main__':
    unittest.main()
