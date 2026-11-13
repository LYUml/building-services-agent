import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.workflow import execute, validate_plan, inventory_source_bindings
from bsa.engine import ProjectError
from tests.test_product_workflow import fixture, ROOT


def plan_fixture(root):
    path,p=fixture(root)
    p['tasks'] += [dict(id='connector',kind='connector_ports',depends_on='convert',basis='place.json'),
                   dict(id='align',kind='product_alignment',junction_from='place',connector_from='connector',basis='place.json'),
                   dict(id='native',kind='alignment_native',depends_on='align'),
                   dict(id='release',kind='manual',requires_pass=['native'])]
    original=p['requirements'][0]
    p['requirements']=[dict(original,id='R'+str(i),task=t['id']) for i,t in enumerate(p['tasks'])]
    path.write_text(json.dumps(p));return path,p


class AlignmentWorkflowTests(unittest.TestCase):
    def test_combined_model_cannot_borrow_input_inventory(self):
        tasks=[dict(id='tee_source',kind='cad_ifc'),
               dict(id='old',kind='ifc_query',depends_on='tee_source'),
               dict(id='tee',kind='product_ports',depends_on='tee_source',requires_pass=['old']),
               dict(id='connector',kind='connector_ports',depends_on='connector_source'),
               dict(id='align',kind='product_alignment',junction_from='tee',connector_from='connector'),
               dict(id='view',kind='ifc_preview',depends_on='align')]
        with self.assertRaisesRegex(ProjectError,'different model'):
            inventory_source_bindings(tasks,ROOT)
        tasks.insert(-1,dict(id='fresh',kind='ifc_query',depends_on='align',refresh_inventory=True))
        tasks[-1]['requires_pass']=['fresh']
        rows=inventory_source_bindings(tasks,ROOT)
        self.assertEqual([r['check'] for r in rows if r['consumer']=='view'],['fresh'])

    def test_missing_producers_leave_diagnostics_pending(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);path,_=plan_fixture(root)
            r=execute(path,root/'run')
            for name in ('align','native','release'):
                self.assertEqual(r['tasks'][name]['status'],'pending')
                self.assertFalse((root/'run'/name).exists())

    def test_wrong_parent_and_replacement_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);path,p=plan_fixture(root)
            p['tasks'][3]['connector_from']='place';path.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError,'matching'):validate_plan(path)
            p['tasks'][3]['connector_from']='connector';p['tasks'][4]['ifc']='source.dwg';path.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError,'inherits'):validate_plan(path)

    def test_mesh_failure_allows_diagnostic_but_blocks_release(self):
        def alignment(*args):
            folder=args[-1];folder.mkdir()
            (folder/'alignment.json').write_text(json.dumps({'model_alignment_pass':True}))
            return {'calculated_checks_pass':False}
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);path,_=plan_fixture(root)
            with patch('bsa.cad_ifc.run',return_value={'geometry_conversion_pass':True}), \
                 patch('bsa.product_ports.run',return_value={'product_ports_pass':True}), \
                 patch('bsa.connector_ports.run',return_value={'connector_ports_pass':True}), \
                 patch('bsa.product_alignment.run',side_effect=alignment), \
                 patch('bsa.alignment_native.run',return_value={'native_clear':True,'mesh_calculated_checks_pass':False}) as native:
                r=execute(path,root/'run',autocad=root/'configured.exe')
            native.assert_called_once()
            self.assertEqual(r['tasks']['align']['status'],'fail')
            self.assertEqual(r['tasks']['native']['status'],'fail')
            self.assertEqual(r['tasks']['release']['status'],'pending')
            self.assertIn('required checks unresolved',r['tasks']['release']['scope'])
