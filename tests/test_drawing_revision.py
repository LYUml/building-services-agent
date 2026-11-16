import copy
import json
from pathlib import Path
import tempfile
import unittest

import ezdxf
from bsa.drawing_document import author
from bsa.drawing_revision import revised,snapshot,compare,artifact_checks,geometry,validate_edits

ROOT=Path(__file__).resolve().parents[1]


class DrawingRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.doc,_=author(json.loads((ROOT/'examples/drawing-document.json').read_text()))
        self.doc.layouts.get('Layout1').add_viewport(center=(100,100),size=(50,30),view_center_point=(0,0),view_height=1)
        obj=next(e for e in self.doc.modelspace().query('TEXT') if e.dxf.text=='PLAN')
        self.edit={'handle':obj.dxf.handle,'expected':{'text':'PLAN','layer':obj.dxf.layer,'insert':list(obj.dxf.insert)[:2]},'replacement':{'text':'PLAN (reviewed "text")','insert':[25,174]}}

    def test_text_revision_preserves_dimensions_symbols_and_papers(self):
        a=self.root/'before.dxf';b=self.root/'after.dxf';self.doc.saveas(a)
        revised(self.doc,[self.edit]);self.doc.saveas(b)
        checked=compare(a,b,[self.edit]);self.assertTrue(checked['blocks_and_paper_entities_preserved'])
        self.assertEqual(len(self.doc.modelspace().query('DIMENSION')),3)
        self.doc.modelspace().query('DIMENSION')[0].dxf.text='wrong measurement';self.doc.saveas(b)
        with self.assertRaisesRegex(ValueError,'outside approved'):compare(a,b,[self.edit])

    def test_all_preconditions_before_any_edit(self):
        before=snapshot(self.doc);bad=copy.deepcopy(self.edit);bad['handle']='FFFF'
        with self.assertRaisesRegex(ValueError,'precondition'):revised(self.doc,[self.edit,bad])
        self.assertEqual(snapshot(self.doc),before)
        bad=copy.deepcopy(self.edit);bad['expected']['insert']=[0,0]
        with self.assertRaisesRegex(ValueError,'precondition'):revised(self.doc,[bad])

    def test_symbol_or_paper_mutation_is_not_approved_text_edit(self):
        a=self.root/'before.dxf';b=self.root/'after.dxf';self.doc.saveas(a)
        revised(self.doc,[self.edit]);self.doc.layouts.get('Layout1').query('VIEWPORT')[0].dxf.height=70;self.doc.saveas(b)
        with self.assertRaisesRegex(ValueError,'outside approved'):compare(a,b,[self.edit])

    def test_missing_native_artifact_cannot_skip_inspection(self):
        with self.assertRaisesRegex(ValueError,'Complete native'):artifact_checks(self.root,{'native_reopen_pass':True,'artifacts':{}})

    def test_line_circle_arc_approved_geometry_changes_and_unlisted_changes(self):
        edits=[]
        for kind in ('line','circle','arc'):
            obj=self.doc.modelspace().query(kind.upper())[0];old=geometry(obj,kind);new=copy.deepcopy(old)
            if kind=='line':new['end'][0]+=2
            else:new['radius']+=1
            if kind=='arc':new['end_angle']=135
            edits.append(dict(handle=obj.dxf.handle,kind=kind,expected=dict(old,layer=obj.dxf.layer),replacement=new))
        a=self.root/'source.dxf';b=self.root/'changed.dxf';self.doc.saveas(a);revised(self.doc,edits);self.doc.saveas(b)
        result=compare(a,b,edits);self.assertEqual(result['edited_entities'],3);self.assertEqual(result['edited_texts'],0)
        self.assertEqual(result['edited_kinds'],{'line':1,'circle':1,'arc':1})
        self.doc.modelspace().query('INSERT')[0].dxf.rotation=90;self.doc.saveas(b)
        with self.assertRaisesRegex(ValueError,'outside approved'):compare(a,b,edits)

    def test_invalid_or_wrong_geometry_prevents_all_edits(self):
        obj=self.doc.modelspace().query('CIRCLE')[0];old=geometry(obj,'circle');e=dict(handle=obj.dxf.handle,kind='circle',expected=dict(old,layer=obj.dxf.layer),replacement=dict(old,radius=0))
        with self.assertRaises(ValueError):validate_edits([e])
        e['replacement']['radius']=4;e['expected']['radius']+=1;before=snapshot(self.doc)
        with self.assertRaisesRegex(ValueError,'precondition'):revised(self.doc,[self.edit,e])
        self.assertEqual(before,snapshot(self.doc))


if __name__=='__main__':unittest.main()
