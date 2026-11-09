import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ezdxf
from bsa.cli import digest
from bsa.cable_route_audit import audit_saved
from bsa.cable_route_drawing import run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class SavedCableAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        source=cls.root/'source';shutil.copytree(ROOT/'examples/cable-coordination',source)
        geometry=json.loads((source/'geometry.json').read_text());geometry['tangent_extensions_m']={'feeder':2.};geometry['buses_m']['DB-A']=[-2.,0.,1.7]
        (source/'geometry.json').write_text(json.dumps(geometry),encoding='utf-8')
        project=json.loads((source/'project.json').read_text());project['lines'][0]['length_m']+=2
        project['sources']['route']=dict(path='geometry.json',sha256=digest(source/'geometry.json'),kind='assumption',locator='Synthetic source geometry')
        project['lines'][0]['length_source']='route';(source/'project.json').write_text(json.dumps(project),encoding='utf-8')
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(source/'project.json',source/'geometry.json',cls.root/'fixture','quarter-straight')
        settings=cls.root/'settings.json';settings.write_text(json.dumps(dict(projection_axes=['X','Z'],annotation_height_m=.04,source='Synthetic drafting test')),encoding='utf-8')
        cls.report=run(source/'project.json',cls.root/'fixture/cables.ifc',cls.root/'fixture/binding.json',settings,cls.root/'drawing')

    def setUp(self):
        self.path=self.root/(self._testMethodName+'.dxf');shutil.copyfile(self.root/'drawing/cable-route.dxf',self.path)
        self.doc=ezdxf.readfile(self.path)

    def check(self):
        self.doc.saveas(self.path)
        r=self.report
        return audit_saved(self.path,r['cable'],r['geometry'],r['settings'],r['obstacles'])

    def test_source_checked_saved_entities(self):
        self.assertEqual(self.check()['entity_count'],16)

    def test_changed_radius_rejected(self):
        self.doc.modelspace().query('ARC[layer=="BSA_CABLE_AXIS"]').first.dxf.radius+=.01
        with self.assertRaisesRegex(ProjectError,'differ'):self.check()

    def test_changed_outline_with_unchanged_axis_rejected(self):
        self.doc.modelspace().query('ARC[layer=="BSA_CABLE_OUTLINE"]').first.dxf.radius+=.005
        with self.assertRaisesRegex(ProjectError,'differ'):self.check()

    def test_false_length_text_rejected(self):
        entity=next(e for e in self.doc.modelspace().query('TEXT') if e.dxf.text.startswith('True total'))
        entity.dxf.text=entity.dxf.text.replace('2.471239','2.424264')
        with self.assertRaisesRegex(ProjectError,'differ'):self.check()

    def test_chord_substitution_rejected(self):
        arc=self.doc.modelspace().query('ARC[layer=="BSA_CABLE_AXIS"]').first
        line=self.doc.modelspace().add_line(arc.start_point,arc.end_point,dxfattribs={'layer':arc.dxf.layer})
        line.set_xdata('BSA_IFC',arc.get_xdata('BSA_IFC'));self.doc.modelspace().delete_entity(arc)
        with self.assertRaisesRegex(ProjectError,'differ'):self.check()

    def test_hidden_entity_rejected(self):
        self.doc.modelspace().query('LINE').first.dxf.invisible=1
        with self.assertRaisesRegex(ProjectError,'visible'):self.check()

    def test_nonplot_layer_rejected(self):
        self.doc.layers.get('BSA_DIMENSION').dxf.plot=0
        with self.assertRaisesRegex(ProjectError,'plot enabled'):self.check()

    def test_wrong_ifc_guid_rejected(self):
        self.doc.modelspace().query('ARC').first.set_xdata('BSA_IFC',[(1000,'unrelated')])
        with self.assertRaisesRegex(ProjectError,'differ'):self.check()

    def test_moved_dimension_text_rejected(self):
        entity=next(e for e in self.doc.modelspace().query('TEXT') if e.dxf.text.startswith('Straight L='))
        entity.dxf.insert=(0.,1.7,0.)
        with self.assertRaisesRegex(ProjectError,'differ'):self.check()

    def test_raw_paper_space_marker_rejected(self):
        entity=self.doc.modelspace().query('TEXT').first
        self.doc.saveas(self.path)
        data=self.path.read_text(encoding='utf-8')
        needle=f'  5\n{entity.dxf.handle}\n'
        self.assertEqual(data.count(needle),1)
        self.path.write_text(data.replace(needle,needle+' 67\n1\n',1),encoding='utf-8')
        r=self.report
        with self.assertRaisesRegex(ProjectError,'visible|differ'):
            audit_saved(self.path,r['cable'],r['geometry'],r['settings'],r['obstacles'])
