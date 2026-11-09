import json
import math
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.api as api
import numpy as np
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase_ifc import inspect

ROOT = Path(__file__).resolve().parents[1]


class ContinuousCableIfcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT / 'runs')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        shutil.copytree(ROOT / 'examples/cable-coordination', cls.root / 'source')
        source = cls.root / 'source'
        author = runpy.run_path(str(ROOT / 'scripts/author_three_phase_ifc_fixture.py'))['run']
        binding = author(source / 'project.json', source / 'geometry.json', cls.root / 'fixture', 'mixed-revolution')
        path = cls.root / 'fixture/cables.ifc'
        model = ifcopenshell.open(str(path))
        cable = model.by_guid(binding['lines']['feeder']['element_guid'])
        reps = {r.RepresentationIdentifier: r for r in cable.Representation.Representations}
        point = lambda p: model.create_entity('IfcCartesianPoint', Coordinates=p)
        direction = lambda p: model.create_entity('IfcDirection', DirectionRatios=p)
        frame = model.create_entity('IfcAxis2Placement3D', Location=point((0., 0., 1.7)),
            Axis=direction((-1., 0., 0.)), RefDirection=direction((0., 1., 0.)))
        straight = model.create_entity('IfcExtrudedAreaSolid', Position=frame, Depth=2.,
            SweptArea=model.create_entity('IfcCircleProfileDef', ProfileType='AREA', Radius=.01),
            ExtrudedDirection=direction((0., 0., 1.)))
        union = api.run('geometry.add_boolean', model, first_item=reps['Body'].Items[0], second_items=[straight], operator='UNION')
        reps['Body'].Items = union
        reps['Body'].RepresentationType = 'CSG'
        arc = reps['Axis'].Items[0]
        line = model.create_entity('IfcPolyline', Points=[point((0., 0., 1.7)), point((-2., 0., 1.7))])
        composite = model.create_entity('IfcCompositeCurve', SelfIntersect=False, Segments=[
            model.create_entity('IfcCompositeCurveSegment', Transition='CONTSAMEGRADIENT', SameSense=True, ParentCurve=arc),
            model.create_entity('IfcCompositeCurveSegment', Transition='DISCONTINUOUS', SameSense=True, ParentCurve=line)])
        reps['Axis'].Items = [composite]
        port = model.by_guid(binding['lines']['feeder']['to_port_guid'])
        port_frame = np.eye(4)
        port_frame[:3, :3] = np.array([[0., 0., -1.], [1., 0., 0.], [0., -1., 0.]])
        port_frame[:3, 3] = [-2., 0., 1.7]
        api.run('geometry.edit_object_placement', model, product=port, matrix=port_frame, is_si=True)
        model.write(str(path))
        binding['ifc_sha256'] = digest(path)
        binding['buses']['DB-A'] = [-2., 0., 1.7]
        geo = cls.root / 'fixture/geometry-source.json'
        data = json.loads(geo.read_text())
        data['scope'] = 'Synthetic quarter plus assumed 2 m tangent extension; no intermediate load or physical joint'
        data['buses_m']['DB-A'] = [-2., 0., 1.7]
        data['tangent_extension_m'] = 2.
        geo.write_text(json.dumps(data), encoding='utf-8')
        binding['source']['sha256'] = digest(geo)
        (cls.root / 'fixture/binding.json').write_text(json.dumps(binding), encoding='utf-8')
        project = json.loads((source / 'project.json').read_text())
        project['lines'][0]['length_m'] += 2
        (source / 'project.json').write_text(json.dumps(project), encoding='utf-8')

    def setUp(self):
        self.case = self.root / self._testMethodName
        shutil.copytree(self.root / 'fixture', self.case)

    def check(self, **kwargs):
        return inspect(self.root / 'source/project.json', self.case / 'cables.ifc', self.case / 'binding.json', **kwargs)

    def test_saved_native_composite(self):
        result = self.check()
        self.assertTrue(result['geometry_correspondence_pass'])
        self.assertEqual(result['lines'][0]['route_geometry'], 'quarter plus tangent straight')
        self.assertAlmostEqual(result['lines'][0]['observed_length_m'], 2 + .3 * math.pi / 2)
        self.assertFalse(result['design_accepted'])

    def test_wrong_port_orientation(self):
        path = self.case / 'cables.ifc'
        model = ifcopenshell.open(str(path))
        next(p for p in model.by_type('IfcDistributionPort') if p.Name == 'to').ObjectPlacement.RelativePlacement.Axis.DirectionRatios = (0., 0., 1.)
        model.write(str(path))
        binding = json.loads((self.case / 'binding.json').read_text())
        binding['ifc_sha256'] = digest(path)
        (self.case / 'binding.json').write_text(json.dumps(binding), encoding='utf-8')
        with self.assertRaisesRegex(ProjectError, 'end-face normal'):
            self.check()

    def test_bend_cannot_be_omitted(self):
        from bsa.cable_bend_limits import run
        source = self.case / 'limits.txt'
        source.write_text('Synthetic bend-limit coverage test; no manufacturer claim.', encoding='utf-8')
        basis = self.case / 'limits.json'
        basis.write_text(json.dumps(dict(version=1, sources={'assumed': dict(path='limits.txt', sha256=digest(source), locator='whole synthetic text', kind='assumption')}, bends={})), encoding='utf-8')
        with self.assertRaisesRegex(ProjectError, 'coverage'):
            run(self.root / 'source/project.json', self.case / 'cables.ifc', self.case / 'binding.json', basis, self.case / 'check')

    def test_derive_true_length_from_stale_project(self):
        from bsa.three_phase_ifc_project import run
        project = json.loads((self.root / 'source/project.json').read_text())
        project['lines'][0]['length_m'] = .3 * math.sqrt(2) + 2
        path = self.root / 'source/stale-project.json'
        path.write_text(json.dumps(project), encoding='utf-8')
        run(path, self.case / 'cables.ifc', self.case / 'binding.json', self.case / 'derived')
        derived = json.loads((self.case / 'derived/project.json').read_text())
        self.assertAlmostEqual(derived['lines'][0]['length_m'], 2 + .3 * math.pi / 2)
        self.assertEqual(json.loads(path.read_text())['lines'][0]['length_m'], project['lines'][0]['length_m'])
