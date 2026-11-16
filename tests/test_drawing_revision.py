import copy
import json
from pathlib import Path
import tempfile
import unittest

import ezdxf
from bsa.drawing_document import author
from bsa.drawing_revision import revised,snapshot,compare,artifact_checks

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


if __name__=='__main__':unittest.main()
