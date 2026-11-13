import unittest
from shapely.geometry import box
from bsa.source_network_tags import select,conflict,audit_selection,audit_saved
from copy import deepcopy
import tempfile
from pathlib import Path
import ezdxf


class SourceTagTests(unittest.TestCase):
    def test_saved_annotations_reject_changed_source_and_duplicate_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.dxf';saved=Path(directory)/'saved.dxf'
            doc=ezdxf.new();doc.appids.new('BSA_IFC');doc.styles.new('BSA_REVIEW_NOTES');doc.layers.new('BSA_COMPONENT_TAG');doc.layers.new('BSA_TAG_LEADER')
            base=doc.modelspace().add_line((0,0),(1,0));doc.saveas(source)
            row=dict(guid='a',tag='N001',point=[2,2],anchor=[1,0],end=[2,2])
            text=doc.modelspace().add_text('N001',dxfattribs=dict(insert=(2,2),height=.1,style='BSA_REVIEW_NOTES',layer='BSA_COMPONENT_TAG'))
            line=doc.modelspace().add_line((1,0),(2,2),dxfattribs=dict(layer='BSA_TAG_LEADER'))
            for e in (text,line):e.set_xdata('BSA_IFC',[(1000,'a')])
            doc.saveas(saved);self.assertTrue(audit_saved(source,saved,[row],.1)['saved_dxf_checked'])
            base.dxf.end=(9,9);doc.saveas(saved)
            with self.assertRaisesRegex(ValueError,'Base drawing changed'):audit_saved(source,saved,[row],.1)
            base.dxf.end=(1,0);line.set_xdata('BSA_IFC',[(1000,'b')]);doc.saveas(saved)
            with self.assertRaises(ValueError):audit_saved(source,saved,[row],.1)

    def test_finite_complete_selection_and_no_space_remains_explicit(self):
        geometry={'a':box(0,0,1,1),'b':box(3,0,4,1)};tags={'a':'N001','b':'N002'}
        r=select(geometry,tags,[],[-2,-2,6,4],.12,per_side=4)
        self.assertEqual({x['guid'] for x in r['selected']},{'a','b'})
        self.assertFalse(conflict(*r['selected'],.12))
        self.assertTrue(audit_selection(geometry,tags,[],[-2,-2,6,4],.12,r['selected'])['graphic_checks_passed'])
        for field,value in [('tag','N999'),('anchor',[.5,.5]),('end',[100,100])]:
            changed=deepcopy(r['selected']);changed[0][field]=value
            with self.assertRaises(ValueError):audit_selection(geometry,tags,[],[-2,-2,6,4],.12,changed)
        with self.assertRaises(ValueError):audit_selection(geometry,tags,[],[-2,-2,6,4],.12,r['selected'][:1])
        missing=select({'a':box(0,0,1,1)},{'a':'N001'},[],[0,0,1,1],.12)
        self.assertIsNone(missing['selected']);self.assertEqual(missing['missing_candidate_guids'],['a'])

    def test_crossing_leaders_and_overlapping_tags_conflict(self):
        a=dict(rectangle=[10,10,11,11],anchor=[0,2],end=[3,2])
        b=dict(rectangle=[14,14,15,15],anchor=[1,1],end=[1,3])
        self.assertTrue(conflict(a,b,.1))
        b.update(rectangle=[10.5,10.5,11.5,11.5],anchor=[6,6],end=[7,7])
        self.assertTrue(conflict(a,b,.1))
