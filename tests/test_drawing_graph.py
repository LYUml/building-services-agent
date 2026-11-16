import copy
import json
from pathlib import Path
import tempfile
import unittest

from bsa import drawing_graph as graph

ROOT=Path(__file__).resolve().parents[1]
DOT=ROOT/'tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin/dot.exe'


@unittest.skipUnless(DOT.is_file(),'Evaluated Graphviz runtime required')
class DrawingGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.project=self.root/'graph.json'
        base=dict(layer='GRAPH',source='Synthetic topology fixture',classification='assumed')
        self.spec=dict(schema='bsa.drawing-graph/1',source='Synthetic topology fixture',source_files=[],nodes=[dict(base,id='A',label='A'),dict(base,id='B',label='B')],edges=[dict(base,id='AB',**{'from':'A','to':'B'})],layers={'GRAPH':dict(color=7,lineweight=18)},notes=[],sheet=dict(paper='A4',window=[0,0,290,200],scale=1,title='Synthetic graph',number='TEST',reference_length=50),layout=dict(origin=[15,50],factor=1,node_width_mm=14,node_height_mm=7,text_height_mm=2,ranksep_mm=5,nodesep_mm=5,rankdir='LR'))

    def save(self):self.project.write_text(json.dumps(self.spec))

    def test_executed_layout_and_wrong_endpoints_or_geometry_rejected(self):
        self.save();r=graph.run(self.project,self.root/'result',graphviz=DOT);self.assertEqual(r['graph']['edges'],1);self.assertFalse(r['native_reopen_pass'])
        layout=json.loads((self.root/'result/graphviz.json').read_text());bad=copy.deepcopy(layout);bad['edges'][0]['tail']=bad['edges'][0]['head']
        with self.assertRaisesRegex(ValueError,'endpoints'):graph.compose(self.spec,bad)
        p=self.root/'result/resolved-document.json';d=json.loads(p.read_text());d['entities'][0]['points'][0][0]+=.1;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'geometry changed'):graph.verify(self.project,self.root/'result')

    def test_missing_runtime_source_changes_and_oversized_labels_rejected(self):
        self.save()
        with self.assertRaises(ValueError):graph.run(self.project,self.root/'missing')
        self.assertFalse((self.root/'missing').exists())
        graph.run(self.project,self.root/'result',graphviz=DOT);layout=json.loads((self.root/'result/graphviz.json').read_text())
        self.spec['nodes'][0]['label']='VERY LONG LABEL THAT CANNOT FIT'
        with self.assertRaisesRegex(ValueError,'fit'):graph.compose(self.spec,layout)
        self.spec['nodes'][0]['label']='A';self.spec['source_files']=[dict(path='graph.json',sha256='0'*64)];self.save()
        with self.assertRaisesRegex(ValueError,'source'):graph.configuration(self.project)


if __name__=='__main__':unittest.main()
