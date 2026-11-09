import math
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
import ifcopenshell
import numpy as np
from bsa.cable_continuity import inspect
from bsa.engine import ProjectError

ROOT = Path(__file__).resolve().parents[1]


class CableContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT / 'runs')
        cls.addClassCleanup(cls.temp.cleanup)
        sys.path.insert(0, str(ROOT / 'scripts'))
        try:
            probe = runpy.run_path(str(ROOT / 'scripts/probe_cable_union.py'))
            cls.out = Path(cls.temp.name) / 'probe'
            probe['run'](cls.out)
        finally:
            sys.path.pop(0)

    def setUp(self):
        self.model = ifcopenshell.open(str(self.out / 'continuous-cable.ifc'))
        reps = {r.RepresentationIdentifier: r for r in self.model.by_type('IfcCableSegment')[0].Representation.Representations}
        self.body, self.axis = reps['Body'].Items[0], reps['Axis'].Items[0]

    def check(self):
        return inspect(self.body, self.axis, np.eye(4), 1., 1.)

    def test_true_length(self):
        self.assertAlmostEqual(self.check()['length'], 2 + .3 * math.pi / 2)

    def test_source_author_roundtrip_and_invalid_extension(self):
        from bsa.cable_continuity import author
        from ifcopenshell.util.shape_builder import ShapeBuilder
        model = ifcopenshell.file(schema='IFC4')
        spec = dict(radius_m=.3, centre_m=[0., 0., 0.], rotation=np.eye(3).tolist())
        solid, curve, ports = author(model, ShapeBuilder(model), spec, .01, 2.)
        result = inspect(solid, curve, np.eye(4), 1., 1.)
        self.assertAlmostEqual(result['length'], 2 + .3 * math.pi / 2)
        np.testing.assert_allclose(ports[-1][:3, 3], [-2., 0., -.3])
        for extension in (0, -1, True, float('nan')):
            with self.assertRaisesRegex(ProjectError, 'extension'):
                author(model, ShapeBuilder(model), spec, .01, extension)

    def test_axis_endpoint_mutation(self):
        self.axis.Segments[1].ParentCurve.Points[1].Coordinates = (-1.9, 0., -.3)
        with self.assertRaisesRegex(ProjectError, 'differs'):
            self.check()

    def test_profile_mismatch(self):
        self.body.SecondOperand.SweptArea.Radius = .011
        with self.assertRaisesRegex(ProjectError, 'equal-radius'):
            self.check()

    def test_disconnected_body_and_axis(self):
        self.body.SecondOperand.Position.Location.Coordinates = (-.1, 0., -.3)
        line = self.axis.Segments[1].ParentCurve
        line.Points[0].Coordinates = (-.1, 0., -.3)
        line.Points[1].Coordinates = (-2.1, 0., -.3)
        with self.assertRaisesRegex(ProjectError, 'meet'):
            self.check()

    def test_false_tangent_declaration(self):
        self.axis.Segments[0].Transition = 'CONTINUOUS'
        with self.assertRaisesRegex(ProjectError, 'tangent'):
            self.check()

    def test_reversed_segment(self):
        self.axis.Segments[1].SameSense = False
        with self.assertRaisesRegex(ProjectError, 'forward'):
            self.check()
