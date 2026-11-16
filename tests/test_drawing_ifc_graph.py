import json
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
import ifcopenshell.api as api
from bsa import drawing_ifc_graph as graph
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]
DOT=ROOT/'tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin/dot.exe'


class IFCGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.model=api.run('project.create_file',version='IFC4');self.a=api.run('root.create_entity',self.model,ifc_class='IfcDuctSegment',name='Synthetic A');self.b=api.run('root.create_entity',self.model,ifc_class='IfcDuctSegment',name='Synthetic B')
        self.ports=[]
        for owner,direction in [(self.a,'SINK'),(self.a,'SOURCE'),(self.b,'SINK'),(self.b,'SOURCE')]:
            port=api.run('system.add_port',self.model,element=owner);port.FlowDirection=direction;self.ports.append(port)
        api.run('system.connect_port',self.model,port1=self.ports[1],port2=self.ports[2],direction='SOURCE')
        self.source=self.root/'source.ifc';self.model.write(str(self.source));self.project=self.root/'graph.json'
        base=dict(source='Explicit synthetic logical topology; no geometry/pressure acceptance',source_files=[],layers={'GRAPH':dict(color=7,lineweight=18)},notes=[],sheet=dict(paper='A4',window=[0,0,290,200],scale=1,title='Synthetic IFC topology',number='TEST',reference_length=50),layout=dict(origin=[15,50],factor=1,node_width_mm=18,node_height_mm=8,text_height_mm=2,ranksep_mm=5,nodesep_mm=5,rankdir='LR'),node_layer='GRAPH',marked_layer='GRAPH',edge_layer='GRAPH')
        self.spec=dict(schema='bsa.drawing-ifc-graph/1',source='Synthetic logical source',ifc='source.ifc',ifc_sha256=digest(self.source),products='all_distribution',marked_products=[self.b.GlobalId],graph=base)

    def save(self):self.project.write_text(json.dumps(self.spec))

    def test_native_directions_boundary_counts_and_explicit_subset(self):
        self.save();resolved,binding,key=graph.compose(self.project,self.root/'out')
        self.assertEqual((binding['products'],binding['ports'],len(binding['interfaces'])),(2,4,1))
        self.assertEqual({p['direction'] for p in binding['open_boundary_ports']},{'SOURCE','SINK'})
        self.assertEqual(binding['interfaces'][0]['from_guid'],self.a.GlobalId);self.assertIn('Synthetic B',key)
        self.spec.update(products=[self.a.GlobalId],marked_products=[]);self.save();_,binding,_=graph.compose(self.project,self.root/'out')
        self.assertEqual(len(binding['external_selected_connections']),1);self.assertEqual(len(binding['interfaces']),0);self.assertEqual(len(binding['open_boundary_ports']),1)

    def test_source_change_ambiguous_direction_and_unselected_mark_rejected(self):
        self.save();self.spec['ifc_sha256']='0'*64;self.save()
        with self.assertRaisesRegex(ValueError,'source'):graph.compose(self.project,self.root/'out')
        self.ports[3].FlowDirection='SOURCEANDSINK';self.model.write(str(self.source));self.spec['ifc_sha256']=digest(self.source);self.save()
        with self.assertRaisesRegex(ValueError,'directions'):graph.compose(self.project,self.root/'out')
        self.ports[3].FlowDirection='SOURCE';self.model.write(str(self.source));self.spec['ifc_sha256']=digest(self.source);self.spec['marked_products']=['not-selected'];self.save()
        with self.assertRaisesRegex(ValueError,'marked'):graph.compose(self.project,self.root/'out')

    @unittest.skipUnless(DOT.is_file(),'Evaluated Graphviz required')
    def test_actual_graph_execution_and_component_key_tamper(self):
        self.save();r=graph.run(self.project,self.root/'result',graphviz=DOT);self.assertTrue(r['integrity_pass']);self.assertFalse(r['native_reopen_pass'])
        self.assertEqual(r['graph']['nodes'],2)
        (self.root/'result/Component Key.csv').write_text('changed')
        with self.assertRaisesRegex(ValueError,'component key'):graph.verify(self.project,self.root/'result')


if __name__=='__main__':unittest.main()
