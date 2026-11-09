import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import ifcopenshell
import numpy as np
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase_ifc import inspect

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/three-phase-network/project.json'
GEOMETRY=ROOT/'examples/three-phase-network/cable-geometry.json'
spec=importlib.util.spec_from_file_location('cable_author',ROOT/'scripts/author_three_phase_ifc_fixture.py')
author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)


class SavedCableBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs',prefix='cable-test-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.fixture=self.root/'fixture'
        author.run(PROJECT,GEOMETRY,self.fixture,'extrusion')
        self.ifc=self.fixture/'cables.ifc';self.binding=self.fixture/'binding.json'

    def check(self,project=PROJECT):
        return inspect(project,self.ifc,self.binding)

    def mutate(self,edit):
        model=ifcopenshell.open(str(self.ifc));edit(model);model.write(str(self.ifc))
        data=json.loads(self.binding.read_text());data['ifc_sha256']=digest(self.ifc)
        self.binding.write_text(json.dumps(data),encoding='utf-8')

    def test_actual_saved_geometry_and_unchanged_sources(self):
        before=digest(self.ifc);report=self.check()
        self.assertTrue(report['geometry_correspondence_pass'])
        self.assertFalse(report['native_electrical_connectivity_verified'])
        self.assertFalse(report['design_accepted'])
        self.assertEqual([r['observed_length_m'] for r in report['lines']],[40.,25.])
        self.assertEqual(digest(self.ifc),before)

    def test_shifted_body_with_unchanged_axis_and_ports_rejected(self):
        def edit(m):
            solid=m.by_type('IfcExtrudedAreaSolid')[0]
            xyz=list(solid.Position.Location.Coordinates);xyz[2]+=.1
            solid.Position.Location.Coordinates=xyz
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'body directrix differs'):self.check()

    def test_shifted_port_rejected(self):
        def edit(m):
            location=m.by_type('IfcDistributionPort')[0].ObjectPlacement.RelativePlacement.Location
            xyz=list(location.Coordinates);xyz[0]+=.1;location.Coordinates=xyz
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'ports do not span'):self.check()

    def test_changed_calculation_length_rejected(self):
        project=self.root/'project.json';shutil.copyfile(PROJECT.parent/'basis.md',self.root/'basis.md')
        data=json.loads(PROJECT.read_text());data['lines'][0]['length_m']+=1
        project.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'route length differs'):self.check(project)

    def test_unit_change_rejected(self):
        self.mutate(lambda m:setattr(m.by_type('IfcSIUnit')[0],'Prefix','MILLI'))
        with self.assertRaisesRegex(ProjectError,'bus anchors'):self.check()

    def test_oblique_extrusion_not_accepted_as_cable(self):
        self.mutate(lambda m:setattr(m.by_type('IfcExtrudedAreaSolid')[0].ExtrudedDirection,'DirectionRatios',(0.1,0.,1.)))
        with self.assertRaisesRegex(ProjectError,'perpendicular'):self.check()

    def test_hollow_extrusion_not_accepted_as_solid_cable(self):
        def edit(m):
            solid=m.by_type('IfcExtrudedAreaSolid')[0]
            solid.SweptArea=m.create_entity('IfcCircleHollowProfileDef',ProfileType='AREA',Radius=.01,WallThickness=.001)
        self.mutate(edit)
        with self.assertRaisesRegex(ProjectError,'solid circle'):self.check()

    def test_unacknowledged_model_change_rejected(self):
        with self.ifc.open('a') as f:f.write('\n')
        with self.assertRaisesRegex(ProjectError,'exact saved IFC hash'):self.check()

    def test_inclined_translated_axes_pass(self):
        geometry=self.root/'inclined.json';data=json.loads(GEOMETRY.read_text())
        angle=.67
        rotation=np.array([[np.cos(angle),0.,np.sin(angle)],[0.,1.,0.],[-np.sin(angle),0.,np.cos(angle)]])
        data['buses_m']={k:(rotation@np.array(v)+[13.,-7.,9.]).tolist() for k,v in data['buses_m'].items()}
        geometry.write_text(json.dumps(data),encoding='utf-8')
        out=self.root/'inclined';author.run(PROJECT,geometry,out,'extrusion')
        result=inspect(PROJECT,out/'cables.ifc',out/'binding.json')
        self.assertTrue(result['geometry_correspondence_pass'])

    def test_source_and_model_hash_changes_rejected(self):
        with (self.fixture/'geometry-source.json').open('a') as f:f.write(' ')
        with self.assertRaisesRegex(ProjectError,'source path/hash'):self.check()
