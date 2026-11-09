import json
from pathlib import Path
import tempfile
import unittest
from bsa.workflow import execute,validate_plan,inventory_source_bindings
from bsa.engine import ProjectError
from test_product_workflow import fixture,ROOT


class ConnectorWorkflowTests(unittest.TestCase):
    def test_missing_failed_and_replacement_producer(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);path,plan=fixture(root);plan['tasks'][1]['kind']='connector_ports';path.write_text(json.dumps(plan))
            for name,engine in (('missing',None),('failed',root/'absent.exe')):
                r=execute(path,root/name,autocad=engine)
                self.assertEqual(r['tasks']['place']['status'],'pending')
                self.assertFalse((root/name/'place').exists())
            plan['tasks'][1]['ifc']='source.dwg';path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ProjectError,'replacement'):validate_plan(path)

    def test_fresh_inventory_for_placed_connector(self):
        tasks=[dict(id='source',kind='cad_ifc'),dict(id='old',kind='ifc_query',depends_on='source'),
               dict(id='placed',kind='connector_ports',depends_on='source',requires_pass=['old']),
               dict(id='new',kind='ifc_query',depends_on='placed',refresh_inventory=True),
               dict(id='view',kind='ifc_preview',depends_on='placed',requires_pass=['new'])]
        rows=inventory_source_bindings(tasks,ROOT)
        self.assertEqual([r['check'] for r in rows if r['consumer']=='view'],['new'])
        tasks[-1]['depends_on']='source'
        with self.assertRaisesRegex(ProjectError,'different model'):inventory_source_bindings(tasks,ROOT)
