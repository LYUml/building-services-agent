import json
import math
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ifcopenshell
import numpy as np
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.quarter_cable import properties
from bsa.three_phase_ifc import inspect
from bsa.three_phase_ifc_project import run as derive

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'examples/three-phase-bend'
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class QuarterCableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        cls.author=staticmethod(runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run'])
        cls.author(SOURCE/'project.json',SOURCE/'geometry.json',cls.root/'fixture','mixed-revolution')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.root_case=self.root/self._testMethodName;shutil.copytree(self.root/'fixture',self.root_case)
        self.ifc=self.root_case/'cables.ifc';self.binding=self.root_case/'binding.json'

    def check(self):return inspect(SOURCE/'project.json',self.ifc,self.binding)

    def mutate(self,edit):
        m=ifcopenshell.open(str(self.ifc));edit(m);m.write(str(self.ifc))
        b=json.loads(self.binding.read_text());b['ifc_sha256']=digest(self.ifc);self.binding.write_text(json.dumps(b),encoding='utf-8')

    def test_native_quarter_volume_and_true_arc_length(self):
        report=self.check();line=report['lines'][0]
        self.assertTrue(report['geometry_correspondence_pass'])
        self.assertEqual(line['route_geometry'],'quarter circle')
        self.assertAlmostEqual(line['observed_length_m'],.3*math.pi/2)
        self.assertGreater(line['observed_length_m'],np.linalg.norm(np.array(line['world_axis_ends_m'])[1]-line['world_axis_ends_m'][0]))
        self.assertAlmostEqual(line['native_volume_m3']/line['analytic_volume_m3'],1,delta=.001)
        self.assertFalse(report['design_accepted'])

    def test_changed_angle_rejected(self):
        self.mutate(lambda m:setattr(m.by_type('IfcRevolvedAreaSolid')[0],'Angle',math.pi/3))
        with self.assertRaisesRegex(ProjectError,'90-degree'):self.check()

    def test_unchanged_endpoints_with_changed_arc_midpoint_rejected(self):
        def edit(m):
            curve=next(c for c in m.by_type('IfcIndexedPolyCurve') if c.Segments and c.Segments[0].is_a('IfcArcIndex'))
            points=[list(p) for p in curve.Points.CoordList];points[1][0]+=.01;curve.Points.CoordList=points
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'Body differs'):self.check()

    def test_polyline_chord_is_not_an_arc(self):
        def edit(m):
            curve=next(c for c in m.by_type('IfcIndexedPolyCurve') if c.Segments and c.Segments[0].is_a('IfcArcIndex'))
            curve.Segments=[m.create_entity('IfcLineIndex',(1,2,3))]
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'ArcIndex'):self.check()

    def test_shifted_body_rejected_with_unchanged_ports(self):
        def edit(m):
            solid=m.by_type('IfcRevolvedAreaSolid')[0];p=list(solid.Position.Location.Coordinates);p[1]+=.01;solid.Position.Location.Coordinates=p
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'Body differs'):self.check()

    def test_self_intersecting_radius_rejected(self):
        self.mutate(lambda m:setattr(m.by_type('IfcRevolvedAreaSolid')[0].SweptArea,'Radius',.31))
        with self.assertRaisesRegex(ProjectError,'non-self-intersecting'):self.check()

    def test_changed_port_axis_at_unchanged_endpoint_rejected(self):
        def edit(m):
            port=next(p for p in m.by_type('IfcDistributionPort') if p.Name=='to')
            port.ObjectPlacement.RelativePlacement.Axis.DirectionRatios=(0.,0.,1.)
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'end-face normal'):self.check()

    def test_compound_rotated_translated_native_arc(self):
        angle=.61;c,s=math.cos(angle),math.sin(angle)
        rotation=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])@np.array([[1.,0.,0.],[0.,c,-s],[0.,s,c]])
        translation=np.array([12.,-3.,8.])
        data=json.loads((SOURCE/'geometry.json').read_text());bend=data['quarter_bends']['feeder']
        bend['centre_m']=(rotation@np.array(bend['centre_m'])+translation).tolist();bend['rotation']=rotation.tolist()
        data['buses_m']={key:(rotation@np.array(value)+translation).tolist() for key,value in data['buses_m'].items()}
        geometry=self.root_case/'placed.json';geometry.write_text(json.dumps(data),encoding='utf-8')
        out=self.root_case/'placed';self.author(SOURCE/'project.json',geometry,out,'mixed-revolution')
        self.assertTrue(inspect(SOURCE/'project.json',out/'cables.ifc',out/'binding.json')['geometry_correspondence_pass'])

    def test_closed_form_canonical_bounds_and_volume_centroid(self):
        result=properties(np.eye(4),.3,.01)
        np.testing.assert_allclose(result['bounds'],[[0.,-.01,-.31],[.31,.01,0.]],atol=1e-14)
        offset=(.3+.01**2/(4*.3))*2/math.pi
        np.testing.assert_allclose(result['centroid'],[offset,0.,-offset],atol=1e-14)

    @unittest.skipUnless(PYTHON,'requires isolated numerical runtime')
    def test_chord_baseline_derives_actual_arc_and_recalculates(self):
        source=self.root_case/'source';shutil.copytree(SOURCE,source)
        project=source/'project.json';p=json.loads(project.read_text());p['lines'][0]['length_m']=.3*math.sqrt(2)
        basis=source/'basis.json';text=json.loads(basis.read_text());text['control']='Deliberately stale chord-length numerical baseline; native saved geometry remains a quarter circle.'
        basis.write_text(json.dumps(text),encoding='utf-8')
        for value in p['sources'].values():value['sha256']=digest(basis)
        project.write_text(json.dumps(p),encoding='utf-8')
        result=derive(project,self.ifc,self.binding,self.root_case/'derived',Path(PYTHON))
        self.assertEqual(result['numerical_status'],'pass')
        self.assertAlmostEqual(result['changes'][0]['derived_length_m'],.3*math.pi/2)
        self.assertAlmostEqual(result['changes'][0]['baseline_length_m'],.3*math.sqrt(2))
        self.assertFalse(result['design_accepted'])
