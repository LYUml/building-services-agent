"""Run with the isolated IfcMCP runtime, not the main engineering environment."""
import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(all(importlib.util.find_spec(module) for module in ('ifcmcp', 'ifcopenshell', 'mcp')),
                     'requires the isolated IfcMCP runtime')
class MCPPropertyTests(unittest.TestCase):
    def test_saved_edit_and_existing_set_rejection(self):
        import ifcopenshell
        import ifcopenshell.api
        from ifcmcp_pump_properties import run

        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);model=root/'original.ifc';patch=root/'patch.json'
            f=ifcopenshell.file(schema='IFC4')
            pump=ifcopenshell.api.run('root.create_entity',f,ifc_class='IfcPump',name='Synthetic test pump')
            f.write(str(model))
            spec=dict(guid=pump.GlobalId,pset='BSA_Test',source='Synthetic integration test',properties={'Review':'Pending'})
            patch.write_text(json.dumps(spec))
            r=asyncio.run(run(model,patch,root/'edited'))
            self.assertTrue(r['property_edit_checks_pass'])
            with self.assertRaisesRegex(ValueError,'already exists'):
                asyncio.run(run(root/'edited/model.ifc',patch,root/'duplicate'))
            self.assertFalse((root/'duplicate').exists())
            spec['properties']['Source']='Untracked override';patch.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError,'reserved'):
                asyncio.run(run(model,patch,root/'bad-source'))
            self.assertFalse((root/'bad-source').exists())


if __name__=='__main__':unittest.main()
