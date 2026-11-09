"""Independent synthetic information controls; no manufacturer geometry."""
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.api as api
from bsa.ids_check import run as check_ids
from bsa.ifc_query import run as query, validate
from bsa.workflow import inventory_source_bindings
from bsa.engine import ProjectError

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT/'tools/ifcmcp-runtime/Scripts/python.exe'


def model(path):
    f = ifcopenshell.file(schema='IFC4')
    api.run('root.create_entity', f, ifc_class='IfcProject', name='Synthetic information test')
    fitting = api.run('root.create_entity', f, ifc_class='IfcPipeFitting')
    ps = api.run('pset.add_pset', f, product=fitting, name='BSA_CADSource')
    api.run('pset.edit_pset', f, pset=ps, properties={k: 'Synthetic presence test' for k in ('Source','DrawingSHA256','SolidHandle','Scope')})
    for i in range(3):
        port = api.run('system.add_port', f, element=fitting)
        port.Name = str(i)
        ps = api.run('pset.add_pset', f, product=port, name='BSA_CADAnchor')
        api.run('pset.edit_pset', f, pset=ps, properties={k: 'Synthetic presence test' for k in ('Source','LineHandle','Endpoint','SourceDXFSHA256','Scope')})
    api.run('root.create_entity', f, ifc_class='IfcDistributionSystem')
    f.write(str(path))
    return f


class ProductInformationTests(unittest.TestCase):
    def test_ids_all_ports_required_and_absence_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); path = root/'model.ifc'; f = model(path)
            ids = ROOT/'examples/ids/cad-product-provenance.ids'
            r = check_ids(ids, path, root/'positive')
            self.assertTrue(r['calculated_checks_pass'])
            self.assertEqual(r['requirements_checked'], 19)
            ps = f.by_type('IfcPropertySet')[-1]
            api.run('pset.edit_pset', f, pset=ps, properties={'LineHandle': None})
            f.write(str(root/'missing.ifc'))
            r = check_ids(ids, root/'missing.ifc', root/'negative')
            self.assertFalse(r['calculated_checks_pass'])
            self.assertEqual(r['requirements_failed'], 1)
            empty = ifcopenshell.file(schema='IFC4'); empty.write(str(root/'empty.ifc'))
            self.assertFalse(check_ids(ids, root/'empty.ifc', root/'empty-check')['calculated_checks_pass'])

    @unittest.skipUnless(PYTHON.is_file(), 'isolated MCP runtime missing')
    def test_actual_mcp_fitting_port_and_system_counts(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); path = root/'model.ifc'; model(path)
            req = root/'counts.json'
            contract = {'source': 'Synthetic minimum count contract', 'minimum_counts': {'IfcPipeFitting':1,'IfcDistributionPort':3,'IfcDistributionSystem':1}}
            req.write_text(json.dumps(contract))
            self.assertTrue(query(path, req, root/'positive', PYTHON)['calculated_checks_pass'])
            contract['minimum_counts']['IfcDistributionPort'] = 4; req.write_text(json.dumps(contract))
            self.assertFalse(query(path, req, root/'negative', PYTHON)['calculated_checks_pass'])

    def test_placement_requires_fresh_inventory(self):
        tasks = [dict(id='body', kind='cad_ifc'), dict(id='old',kind='ifc_query',depends_on='body'),
                 dict(id='placed',kind='product_ports',depends_on='body',requires_pass=['old']),
                 dict(id='audit',kind='ids_check',depends_on='placed')]
        with self.assertRaisesRegex(ProjectError, 'different model'):
            inventory_source_bindings(tasks, ROOT)
        tasks.insert(-1, dict(id='fresh',kind='ifc_query',depends_on='placed',refresh_inventory=True))
        tasks[-1]['requires_pass'] = ['fresh']
        rows = inventory_source_bindings(tasks, ROOT)
        self.assertEqual([r['check'] for r in rows if r['consumer']=='audit'], ['fresh'])
        tasks[-1]['depends_on'] = 'body'
        with self.assertRaisesRegex(ProjectError, 'different model'):
            inventory_source_bindings(tasks, ROOT)

    def test_unsupported_or_nonpositive_count_rejected(self):
        for counts in ({'IfcWall':1}, {'IfcDistributionPort':0}, {'IfcPipeFitting':True}):
            with self.assertRaises(ProjectError): validate({'source':'Synthetic', 'minimum_counts':counts})
