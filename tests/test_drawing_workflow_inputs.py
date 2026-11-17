import json
from pathlib import Path
import tempfile
import unittest
from bsa import drawing_access
from bsa.cli import digest
from bsa.workflow import execute,verify

ROOT=Path(__file__).resolve().parents[1]

class DrawingWorkflowInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def stage(self,name):
        p=self.root/(name+'.json');p.write_bytes((ROOT/'examples'/('drawing-'+name+'.json')).read_bytes());return p

    def test_embedded_layout_and_labels_pin_actual_upstream_files(self):
        for name,pin in [('layout','rectpack-0.2.2.json'),('labels','textalloc-1.2.4.json')]:
            project=self.stage(name);files=drawing_access.workflow_inputs(project)
            self.assertIn(ROOT/'third_party'/pin,files)
            self.assertTrue(any('site-packages' in str(p) and p.name=='__init__.py' for p in files))
            self.assertIn(ROOT/'src/bsa/drawing_document.py',files)
            self.assertFalse(drawing_access.needs_graphviz(project))

    def test_graph_source_hash_and_missing_runtime(self):
        project=self.stage('graph');data=json.loads(project.read_text());note=self.root/'source.md';note.write_text('Synthetic source')
        data['source_files']=[dict(path='source.md',sha256=digest(note))];project.write_text(json.dumps(data))
        self.assertIn(note,drawing_access.workflow_inputs(project));self.assertTrue(drawing_access.needs_graphviz(project))
        plan=json.loads((ROOT/'examples/drawing-workflow-plan.json').read_text());plan['tasks'][0]['project']=project.name;plan['brief']='brief.md'
        (self.root/'brief.md').write_bytes((ROOT/'examples/drawing-workflow/brief.md').read_bytes());p=self.root/'plan.json';p.write_text(json.dumps(plan))
        # Graphviz absence must stop before any native CAD runtime is needed.
        # Use this existing inert file as a host-path sentinel; never execute it.
        result=execute(p,self.root/'missing-graphviz',autocad=Path(__file__))
        self.assertEqual(result['tasks']['sheet']['status'],'pending');self.assertIn('Graphviz',result['tasks']['sheet']['scope'])
        self.assertFalse((self.root/'missing-graphviz/sheet').exists());self.assertTrue(verify(self.root/'missing-graphviz')['integrity_pass'])
        note.write_text('Changed')
        with self.assertRaises(ValueError):drawing_access.workflow_inputs(project)

    def test_ifc_metadata_does_not_bypass_source_workspace_and_hash(self):
        # This is only an input-binding control: dummy bytes are never called IFC geometry.
        source=self.root/'source.ifc';source.write_text('Not a model; no native execution')
        for schema in ['bsa.drawing-ifc-sections/1','bsa.drawing-ifc-graph/1']:
            spec=dict(schema=schema,ifc='source.ifc',ifc_sha256=digest(source),graph=dict(source_files=[]))
            project=self.root/'ifc.json';project.write_text(json.dumps(spec))
            self.assertIn(source,drawing_access.workflow_inputs(project))
            spec['ifc_sha256']='0'*64;project.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):drawing_access.workflow_inputs(project)
            spec['ifc']=str(source);project.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):drawing_access.workflow_inputs(project)

if __name__=='__main__':unittest.main()
