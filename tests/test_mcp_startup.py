"""Startup must not depend on unrelated optional native engineering imports."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from bsa import mcp_worker

ROOT=Path(__file__).resolve().parents[1]

class MCPStartupTests(unittest.TestCase):
    def test_server_import_with_optional_native_imports_denied(self):
        code='''import importlib.abc,sys,asyncio
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'shapely','ifcopenshell','fluids','cadquery','matplotlib'}:
   raise ImportError('Unexpected optional engine at MCP startup: '+fullname)
sys.meta_path.insert(0,Deny())
from bsa.mcp_server import create_server
server=create_server()
tools=asyncio.run(server.list_tools())
assert {'bsa_draw_document','bsa_verify_ifc_port_bcf','bsa_verify_delivery_archive'} <= {t.name for t in tools}
print('Required tools available without optional native engines')
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Required tools',result.stdout)

    def test_unregistered_operation_cannot_import_anything(self):
        with patch('bsa.mcp_worker.importlib.import_module') as load:
            for operation in ['os.system','bsa.cli.main','bsa.drawing_access.__dict__']:
                with self.assertRaises(ValueError):mcp_worker.resolve(operation)
        load.assert_not_called()

    def test_worker_reports_error_as_json_without_startup_crash(self):
        result=subprocess.run([sys.executable,'-m','bsa.mcp_worker'],input=json.dumps(dict(operation='os.system',args=[],kwargs={})),cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,2)
        response=json.loads(result.stdout);self.assertFalse(response['ok']);self.assertIn('registered',response['error'])

if __name__=='__main__':unittest.main()
