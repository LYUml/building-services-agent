import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from bsa.drawing_layout import compose,run,verify

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('rectpack'),'Pinned optional rectpack required')
class DrawingLayoutTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads((ROOT/'examples/drawing-layout.json').read_text())

    def test_packing_keeps_views_separate_and_preserves_dimensions(self):
        before=copy.deepcopy(self.spec);document,layout=compose(self.spec)
        self.assertEqual(self.spec,before);self.assertEqual(compose(self.spec),(document,layout))
        regions=[r['padded_region'] for r in layout['placements'].values()]
        for i,a in enumerate(regions):
            for b in regions[i+1:]:self.assertFalse(min(a[2],b[2])>max(a[0],b[0])+1e-8 and min(a[3],b[3])>max(a[1],b[1])+1e-8)
        by={e['id']:e for e in document['entities']}
        for view in self.spec['views']:
            delta=layout['placements'][view['id']]['translation']
            for e in view['entities']:
                actual=by[e['id']]
                if e['kind']=='dimension':
                    self.assertEqual(actual['distance'],e['distance'])
                    for j in range(2):self.assertAlmostEqual(actual['p2'][j]-actual['p1'][j],e['p2'][j]-e['p1'][j])
                if 'radius' in e:self.assertEqual(actual['radius'],e['radius'])
                if 'insert' in e:self.assertEqual(actual['insert'],[e['insert'][j]+delta[j] for j in range(2)])

    def test_unplaced_views_and_reserved_regions_rejected(self):
        for mutation in ('too-large','frame'):
            s=copy.deepcopy(self.spec)
            if mutation=='too-large':s['content_window']=[8,28,30,48]
            else:s['content_window'][1]=10
            with self.assertRaises(ValueError):compose(s)

    def test_reconstruct_packed_document_rejects_edits(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);p=root/'layout.json';p.write_text(json.dumps(self.spec));r=run(p,root/'result')
            self.assertTrue(r['integrity_pass']);self.assertFalse(r['native_reopen_pass'])
            self.assertEqual(r['artifacts'][0]['path'],'drawing/Drawing.dxf')
            out=root/'result/resolved-document.json';d=json.loads(out.read_text());d['entities'][0]['layer']='ANNOTATION';out.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'Packed document'):verify(p,root/'result')


if __name__=='__main__':unittest.main()
