import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.bim import validate,run
from bsa.engine import ProjectError
from bsa.workflow import execute,passages
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/mep-ifc/project.json'


class BIMTests(unittest.TestCase):
    def test_rejects_geometry_identity_and_topology_errors(self):
        source=json.loads(PROJECT.read_text())
        for change in (lambda p:p['devices'][0].update(origin_m=[-1,0,0]),
                       lambda p:p['devices'][0].update(size_m=[0,1,1]),
                       lambda p:p['devices'][0].update(ifc_class='IfcWall'),
                       lambda p:p['devices'][0].update(source='unknown'),
                       lambda p:p['connections'][0].update(to='missing.port'),
                       lambda p:p['devices'][1]['ports'][0].update(direction='SOURCE'),
                       lambda p:p.update(project_uuid='not-a-uuid')):
            p=copy.deepcopy(source);change(p)
            with self.assertRaises(ProjectError):validate(p)

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'optional IFC dependency')
    def test_real_ifc_schema_geometry_and_connectivity(self):
        with tempfile.TemporaryDirectory() as folder:
            r=run(PROJECT,Path(folder)/'ifc')
            self.assertTrue(all(r['checks'].values()))
            self.assertFalse(r['design_accepted'])
            self.assertEqual({d['id'] for d in r['devices']},{'DB1','L1'})
            self.assertEqual(next(d for d in r['devices'] if d['id']=='L1')['bounds_m'],[[2,3,2.7],[2.6,3.6,2.75]])
            with self.assertRaises(FileExistsError):run(PROJECT,Path(folder)/'ifc')

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'optional IFC dependency')
    def test_bim_adapter_in_source_linked_workflow(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);brief=root/'brief.md'
            brief.write_text('Create the synthetic IFC envelope model.\n',encoding='utf-8')
            (root/'project.json').write_bytes(PROJECT.read_bytes())
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='bim',kind='bim',project='project.json')],
                requirements=[dict(id='R1',passage='P001',quote=passages(brief)[0]['text'],task='bim',acceptance='schema and geometry checks')])
            plan_path=root/'plan.json';plan_path.write_text(json.dumps(plan),encoding='utf-8')
            r=execute(plan_path,root/'run')
            self.assertTrue(r['execution_pass'])
            self.assertIn('bim/model.ifc',r['requirements'][0]['evidence'])
            self.assertEqual(r['requirements'][0]['acceptance_status'],'pending review')


if __name__=='__main__':unittest.main()
