import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ifcopenshell
from bsa.cli import digest
from bsa.ifc_obstacles import run as append
from bsa.three_phase_coordination import run

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'examples/cable-coordination'


class CurvedCableCoordinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(SOURCE/'project.json',SOURCE/'geometry.json',cls.root/'base','mixed-revolution')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def stage(self,name,y):
        source=self.root/name;shutil.copytree(SOURCE,source)
        basis=source/'basis.json';data=json.loads(basis.read_text());data['obstacle']['origin_m'][1]=y
        basis.write_text(json.dumps(data),encoding='utf-8')
        p=json.loads((source/'project.json').read_text())
        for record in p['sources'].values():record['sha256']=digest(basis)
        (source/'project.json').write_text(json.dumps(p),encoding='utf-8')
        inventory=json.loads((source/'obstacles.json').read_text());inventory['obstacles'][0]['origin_m'][1]=y;inventory['sources']['assumed']['sha256']=digest(basis)
        (source/'obstacles.json').write_text(json.dumps(inventory),encoding='utf-8')
        policy=json.loads((source/'policy.json').read_text());policy['sources']['assumed']='Synthetic 30 mm clearance target and numerical tolerances in basis.json SHA256 '+digest(basis)+'; no contact waivers or code claim'
        (source/'policy.json').write_text(json.dumps(policy),encoding='utf-8')
        append(self.root/'base/cables.ifc',source/'obstacles.json',source/'combined')
        b=json.loads((self.root/'base/binding.json').read_text());b['ifc_sha256']=digest(source/'combined/model.ifc')
        (source/'combined/binding.json').write_text(json.dumps(b),encoding='utf-8')
        shutil.copyfile(self.root/'base/geometry-source.json',source/'combined/geometry-source.json')
        return source

    def check(self,source):return run(source/'project.json',source/'combined/model.ifc',source/'combined/binding.json',source/'policy.json',source/'check')

    def test_actual_clear_cable_and_obstacle(self):
        source=self.stage('safe',.10);r=self.check(source)
        self.assertEqual(r['status'],'pass');self.assertEqual(r['checked_elements'],2)
        self.assertFalse(r['design_accepted'])

    def test_clearance_failure_without_material_overlap(self):
        source=self.stage('near',.025);r=self.check(source)
        self.assertEqual(r['status'],'fail');self.assertEqual(r['intersection_pair_count'],0)
        self.assertGreater(r['clearance_violation_pair_count'],0)

    def test_actual_material_intrusion_rejected(self):
        source=self.stage('overlap',-.005);r=self.check(source)
        self.assertEqual(r['status'],'fail');self.assertGreater(r['intersection_pair_count'],0)
        detail=json.loads((source/'check/clash/clash.json').read_text())
        self.assertTrue(any(row.get('overlap_volume_m3',0)>0 for row in detail['intersections']))

    def test_missing_other_element_geometry_cannot_pass_coverage(self):
        source=self.stage('missing',.10);path=source/'combined/model.ifc';m=ifcopenshell.open(str(path))
        m.create_entity('IfcBuildingElementProxy',GlobalId=ifcopenshell.guid.new(),Name='Missing geometry obstacle');m.write(str(path))
        binding=source/'combined/binding.json';b=json.loads(binding.read_text());b['ifc_sha256']=digest(path);binding.write_text(json.dumps(b),encoding='utf-8')
        r=self.check(source);self.assertEqual(r['status'],'fail');self.assertFalse(r['clash_checks']['geometry_coverage'])
