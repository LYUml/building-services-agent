import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from bsa.drawing_labels import compose,run,verify,intersects

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('textalloc'),'Pinned optional textalloc required')
class DrawingLabelTests(unittest.TestCase):
    def setUp(self):self.spec=json.loads((ROOT/'examples/drawing-labels.json').read_text())

    def test_conflicting_labels_allocated_without_geometry_or_identity_changes(self):
        before=copy.deepcopy(self.spec);document,report=compose(self.spec)
        self.assertEqual(before,self.spec);self.assertEqual(compose(self.spec),(document,report))
        self.assertEqual(report['labels'],3);self.assertEqual(report['leaders'],3)
        self.assertGreaterEqual(report['protected_source_text_boxes'],1)
        by={e['id']:e for e in document['entities']};selected={x['id'] for x in self.spec['labels']}
        for e in self.spec['document']['entities']:
            if e['id'] not in selected:self.assertEqual(by[e['id']],e)
            else:self.assertEqual(by[e['id']]['text'],e['text'])
        for i,row in enumerate(report['placements']):
            self.assertEqual(by['leader:'+row['id']]['start'],row['anchor'])
            self.assertEqual(row['target'],next(x['target'] for x in self.spec['labels'] if x['id']==row['id']))
            for other in report['placements'][i+1:]:self.assertFalse(intersects(row['box'],other['box']))

    def test_unplaceable_label_and_invalid_target_rejected(self):
        for mode in ('unplaceable','target','rotated'):
            with self.subTest(mode=mode):
                s=copy.deepcopy(self.spec)
                if mode=='unplaceable':s['document']['entities'][3]['text']='X'*1000
                elif mode=='target':s['labels'][0]['target']='missing'
                else:s['document']['entities'][3]['rotation']=90
                with self.assertRaises(ValueError):compose(s)

    def test_saved_label_modification_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);p=root/'labels.json';p.write_text(json.dumps(self.spec));r=run(p,root/'result')
            self.assertTrue(r['integrity_pass']);self.assertFalse(r['native_reopen_pass'])
            out=root/'result/resolved-document.json';d=json.loads(out.read_text());d['entities'][-1]['end'][0]+=1;out.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'source replay'):verify(p,root/'result')


if __name__=='__main__':unittest.main()
