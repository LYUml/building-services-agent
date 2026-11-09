import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.element as element
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_obstacles import run as append
from bsa.obstacle_projection import extract

ROOT=Path(__file__).resolve().parents[1]


class ObstacleProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        shutil.copytree(ROOT/'examples/cable-coordination',cls.root/'source')
        source=cls.root/'source'
        geometry=json.loads((source/'geometry.json').read_text())
        geometry['tangent_extensions_m']={'feeder':2.}
        geometry['buses_m']['DB-A']=[-2.,0.,1.7]
        (source/'geometry.json').write_text(json.dumps(geometry),encoding='utf-8')
        project=json.loads((source/'project.json').read_text());project['lines'][0]['length_m']+=2
        project['sources']['route']=dict(path='geometry.json',sha256=digest(source/'geometry.json'),kind='assumption',locator='Synthetic extension and anchors')
        project['lines'][0]['length_source']='route'
        (source/'project.json').write_text(json.dumps(project),encoding='utf-8')
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(source/'project.json',source/'geometry.json',cls.root/'cable','quarter-straight')
        append(cls.root/'cable/cables.ifc',source/'obstacles.json',cls.root/'combined')

    def setUp(self):
        self.path=self.root/(self._testMethodName+'.ifc')
        shutil.copyfile(self.root/'combined/model.ifc',self.path)

    def check(self):return extract(self.path,self.root/'source/obstacles.json',['X','Z'])

    def test_native_projection_and_separate_depth(self):
        rows,files=self.check();self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['depth_axis'],'Y')
        for a,b in zip(rows[0]['projected_bounds_m'],[.19,1.76,.23,1.82]):self.assertAlmostEqual(a,b)
        for a,b in zip(rows[0]['depth_interval_m'],[.1,.14]):self.assertAlmostEqual(a,b)
        self.assertAlmostEqual(rows[0]['native_volume_m3'],.04*.04*.06)
        self.assertIn(str(self.path.resolve()),files)

    def test_shifted_native_box_rejected(self):
        model=ifcopenshell.open(str(self.path));obj=model.by_type('IfcBuildingElementProxy')[0]
        coords=list(obj.ObjectPlacement.RelativePlacement.Location.Coordinates);coords[0]+=.01
        obj.ObjectPlacement.RelativePlacement.Location.Coordinates=coords;model.write(str(self.path))
        with self.assertRaisesRegex(ProjectError,'bounds differ'):self.check()

    def test_wrong_saved_provenance_rejected(self):
        model=ifcopenshell.open(str(self.path));obj=model.by_type('IfcBuildingElementProxy')[0]
        pset=model.by_id(element.get_psets(obj)['BSA_CoordinationObstacle']['id'])
        api.run('pset.edit_pset',model,pset=pset,properties={'SourceSHA256':'0'*64});model.write(str(self.path))
        with self.assertRaisesRegex(ProjectError,'provenance'):self.check()

    def test_wrong_identity_rejected(self):
        model=ifcopenshell.open(str(self.path));model.by_type('IfcBuildingElementProxy')[0].Name='unrelated';model.write(str(self.path))
        with self.assertRaisesRegex(ProjectError,'identity'):self.check()

    def test_invalid_projection_axes_rejected(self):
        for axes in (['X','X'],['X',{}],['X']):
            with self.assertRaisesRegex(ProjectError,'axes'):extract(self.path,self.root/'source/obstacles.json',axes)

    def test_extra_physical_element_blocks_drawing(self):
        from bsa.cable_route_drawing import run
        case=self.root/'coverage';case.mkdir()
        model=ifcopenshell.open(str(self.path))
        api.run('root.create_entity',model,ifc_class='IfcBuildingElementProxy',name='Unlisted equipment')
        model.write(str(self.path))
        binding=json.loads((self.root/'cable/binding.json').read_text());binding['ifc_sha256']=digest(self.path)
        (case/'binding.json').write_text(json.dumps(binding),encoding='utf-8')
        shutil.copyfile(self.root/'cable/geometry-source.json',case/'geometry-source.json')
        settings=case/'settings.json';settings.write_text(json.dumps(dict(projection_axes=['X','Z'],annotation_height_m=.04,source='Synthetic test drafting settings')),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'complete physical element coverage'):
            run(self.root/'source/project.json',self.path,case/'binding.json',settings,case/'drawing',obstacles=self.root/'source/obstacles.json')
        self.assertFalse((case/'drawing').exists())
