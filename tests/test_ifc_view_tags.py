import json
from pathlib import Path
import shutil
import tempfile
import unittest
import ezdxf
from bsa.bim import run as author
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_views import run,verify_manifest
from bsa.route_drawing_qa import enters
from bsa.view_tags import rectangle,audit_positions

ROOT=Path(__file__).resolve().parents[1]


class IFCViewTagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        author(ROOT/'examples/circulation-ifc/model.json',cls.root/'model')
        run(cls.root/'model/model.ifc',ROOT/'examples/circulation-ifc/views-settings.json',cls.root/'views')

    def test_actual_saved_tags_avoid_all_saved_axis_and_marker_strokes(self):
        p=verify_manifest(self.root/'views/views.json');height=p['settings']['annotation_height_m']
        for view in p['views']:
            doc=ezdxf.readfile(self.root/'views'/view['dxf']);strokes=[e for e in doc.modelspace() if e.dxftype()=='LINE']
            self.assertFalse(list(doc.modelspace().query('LINE[layer=="BSA_LEADER"]')))
            self.assertEqual(len(view['segments']),4)
            for row in view['segments']:
                tag=doc.entitydb[row['handles'][-2]];self.assertEqual(tag.dxftype(),'TEXT');self.assertTrue(tag.dxf.text.startswith('['))
                box=rectangle(list(tag.dxf.insert)[:2],tag.dxf.text,height)
                for line in strokes:self.assertFalse(enters(list(line.dxf.start)[:2],list(line.dxf.end)[:2],box))

    def mutated(self,name,transform):
        folder=self.root/name;shutil.copytree(self.root/'views',folder);path=folder/'views.json';p=json.loads(path.read_text());view=p['views'][0]
        drawing=folder/view['dxf'];doc=ezdxf.readfile(drawing);tag=doc.entitydb[view['segments'][0]['handles'][-2]];transform(tag);doc.saveas(drawing)
        p['artifacts'][view['dxf']]=digest(drawing);path.write_text(json.dumps(p));return path

    def test_moved_or_reassigned_tag_cannot_pass_with_updated_file_hash(self):
        for name,change in [('moved',lambda t:setattr(t.dxf,'insert',(2.5,3,0))),('identity',lambda t:setattr(t.dxf,'text','[99]')),('width',lambda t:setattr(t.dxf,'width',2))]:
            with self.subTest(name=name),self.assertRaisesRegex(ProjectError,'source-keyed tag differs'):verify_manifest(self.mutated(name,change))

    def test_omitted_helper_pin_and_graphic_overlap_reject(self):
        path=self.root/'views/views.json';p=json.loads(path.read_text());p['inputs'].pop(str((ROOT/'src/bsa/view_tags.py').resolve()));copy=self.root/'views/omitted.json';copy.write_text(json.dumps(p))
        with self.assertRaisesRegex(ProjectError,'helper method pin'):verify_manifest(copy)
        with self.assertRaisesRegex(ProjectError,'intersects'):audit_positions([dict(point=[1,1],text='[1]')],[[.5,.5,2,2]],[],[0,0,5,5],.1)
