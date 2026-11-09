import json
import math
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ifcopenshell
import numpy as np
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase_ifc import inspect

ROOT=Path(__file__).resolve().parents[1]


class LeadQuarterTailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        stage=runpy.run_path(str(ROOT/'scripts/run_continuous_cable_demo.py'))['run']
        stage(cls.root/'base',None,lead=1.2)

    def setUp(self):
        self.case=self.root/self._testMethodName
        shutil.copytree(self.root/'base/fixture',self.case)
        self.project=self.root/'base/source/project.json'

    def check(self):return inspect(self.project,self.case/'cables.ifc',self.case/'binding.json')

    def mutate(self,edit):
        path=self.case/'cables.ifc';model=ifcopenshell.open(str(path));edit(model);model.write(str(path))
        binding=json.loads((self.case/'binding.json').read_text());binding['ifc_sha256']=digest(path)
        (self.case/'binding.json').write_text(json.dumps(binding),encoding='utf-8')

    def test_native_saved_volume_length_and_ports(self):
        result=self.check();row=result['lines'][0]
        self.assertEqual(row['route_geometry'],'straight plus quarter plus straight')
        self.assertAlmostEqual(row['observed_length_m'],1.2+.3*math.pi/2+2)
        self.assertAlmostEqual(row['native_volume_m3']/row['analytic_volume_m3'],1,delta=.001)
        np.testing.assert_allclose(row['world_axis_ends_m'],[[.3,0.,3.2],[-2.,0.,1.7]])
        self.assertFalse(result['design_accepted'])

    def test_lead_radius_mismatch_rejected(self):
        def edit(model):
            solid=next(s for s in model.by_type('IfcExtrudedAreaSolid') if abs(s.Depth-1.2)<1e-9)
            # The author may share the circular profile between straight leaves.
            profile=model.create_entity('IfcCircleProfileDef',ProfileType='AREA',Radius=.011)
            solid.SweptArea=profile
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'equal-radius'):self.check()

    def test_disconnected_lead_and_axis_rejected(self):
        def edit(model):
            solid=next(s for s in model.by_type('IfcExtrudedAreaSolid') if abs(s.Depth-1.2)<1e-9)
            coords=list(solid.Position.Location.Coordinates);coords[0]+=.01;solid.Position.Location.Coordinates=coords
            line=model.by_type('IfcCompositeCurve')[0].Segments[0].ParentCurve
            for point in line.Points:
                coords=list(point.Coordinates);coords[0]+=.01;point.Coordinates=coords
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'meet'):self.check()

    def test_lead_port_axis_rejected(self):
        self.mutate(lambda m:setattr(next(p for p in m.by_type('IfcDistributionPort') if p.Name=='from').ObjectPlacement.RelativePlacement.Axis,'DirectionRatios',(0.,1.,0.)))
        with self.assertRaisesRegex(ProjectError,'end-face normal'):self.check()

    def test_bend_coverage_required(self):
        from bsa.cable_bend_limits import run
        source=self.case/'basis.txt';source.write_text('Synthetic omitted-bend coverage control',encoding='utf-8')
        basis=self.case/'limits.json';basis.write_text(json.dumps(dict(version=1,sources={'assumed':dict(path='basis.txt',sha256=digest(source),locator='whole test text',kind='assumption')},bends={})),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'coverage'):run(self.project,self.case/'cables.ifc',self.case/'binding.json',basis,self.case/'limits')

    def test_route_writer_keeps_lead_and_auditor_rejects_its_removal(self):
        from bsa.cable_route_drawing import run
        from bsa.cable_route_audit import audit_saved
        import ezdxf
        settings=self.case/'settings.json';settings.write_text(json.dumps(dict(projection_axes=['X','Z'],annotation_height_m=.04,source='Synthetic draft control')),encoding='utf-8')
        report=run(self.project,self.case/'cables.ifc',self.case/'binding.json',settings,self.case/'drawing')
        self.assertAlmostEqual(report['lead_length_m'],1.2)
        path=self.case/'drawing/cable-route.dxf';doc=ezdxf.readfile(path)
        lead=doc.modelspace().query('LINE[layer=="BSA_CABLE_LEAD_AXIS"]').first
        self.assertAlmostEqual(lead.dxf.start.distance(lead.dxf.end),1.2)
        doc.modelspace().delete_entity(lead);doc.saveas(path)
        with self.assertRaisesRegex(ProjectError,'differ'):
            audit_saved(path,report['cable'],report['geometry'],report['settings'],report['obstacles'])

    def test_compound_rotated_translated_native_geometry(self):
        from bsa.quarter_cable import source_geometry
        source=self.case/'rotated-source';shutil.copytree(self.root/'base/source',source)
        theta=.61;phi=.38;c,s=math.cos(theta),math.sin(theta);a,b=math.cos(phi),math.sin(phi)
        rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])@np.array([[1,0,0],[0,a,-b],[0,b,a]])
        data=json.loads((source/'geometry.json').read_text());spec=data['quarter_bends']['feeder']
        spec.update(centre_m=[12.,-3.,8.],rotation=rotation.tolist())
        _,frame,points=source_geometry(spec,.01)
        data['buses_m']['source']=(points[0]+frame[:3,2]*1.2).tolist()
        data['buses_m']['DB-A']=(points[-1]-frame[:3,0]*2).tolist()
        (source/'geometry.json').write_text(json.dumps(data),encoding='utf-8')
        p=json.loads((source/'project.json').read_text());p['sources']['route']['sha256']=digest(source/'geometry.json')
        (source/'project.json').write_text(json.dumps(p),encoding='utf-8')
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(source/'project.json',source/'geometry.json',self.case/'rotated','straight-quarter-straight')
        result=inspect(source/'project.json',self.case/'rotated/cables.ifc',self.case/'rotated/binding.json')
        self.assertTrue(result['geometry_correspondence_pass'])
