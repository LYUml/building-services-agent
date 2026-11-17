import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


class RecoveryImportTests(unittest.TestCase):
    def test_pump_dispatch_does_not_import_optional_fan_geometry(self):
        code='''import importlib.abc,json,sys
class BlockGeometry(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'manifold3d','ifcopenshell'}:
   raise ModuleNotFoundError('Unrelated geometry dependency requested: '+fullname,name=fullname)
sys.meta_path.insert(0,BlockGeometry())
from bsa import pump_catalogue_iteration,recovery_controller
from bsa.catalogue_iteration import selection_modules
assert all('fan' not in m.__name__ for m in selection_modules({'kind':'pump_operating_point'}))
assert 'bsa.circular_fan_selection' not in sys.modules
assert 'bsa.rectangular_binding' not in sys.modules
print(json.dumps({'pump_dispatch_without_geometry':True}))
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['pump_dispatch_without_geometry'])


if __name__=='__main__':unittest.main()
