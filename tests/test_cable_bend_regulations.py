import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.element as element
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.cable_bend_regulations import run

ROOT=Path(__file__).resolve().parents[1]
SOURCES=os.environ.get('BSA_TEST_HK_CABLE_SOURCES')


@unittest.skipUnless(SOURCES,'requires pinned official Wiring CoP PDF')
class NativeCableRuleBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        demo=runpy.run_path(str(ROOT/'scripts/run_hk_cable_bend_demo.py'))['run']
        cls.result=demo(cls.root/'suite',Path(SOURCES))

    def setUp(self):
        self.case=self.root/self._testMethodName
        for folder in ('source','selected-model'):shutil.copytree(self.root/'suite/scoped-pass'/folder,self.case/folder)
        self.basis=self.case/'source/rule-basis.json'

    def check(self):
        return run(self.case/'source/project.json',self.case/'selected-model/cables.ifc',self.case/'selected-model/binding.json',self.basis,ROOT/'regulations/hk/cable-bends-2026.11.10/pack.json',Path(SOURCES),self.case/'new-check')

    def alter_basis(self,key,value):
        p=json.loads(self.basis.read_text());p['bends']['feeder'][key]=value;self.basis.write_text(json.dumps(p),encoding='utf-8')

    def test_actual_official_four_scenarios(self):
        self.assertTrue(self.result['expected_behaviors_pass'])
        self.assertEqual([r['report']['status'] for r in self.result['scenarios']],['pass','fail','pending','pending'])
        self.assertFalse(self.result['design_accepted'])

    def test_diameter_mismatch_rejected(self):
        self.alter_basis('overall_diameter_mm',25.)
        with self.assertRaisesRegex(ProjectError,'envelope differs'):self.check()

    def test_product_source_mismatch_rejected(self):
        self.alter_basis('product_reference','unrelated product')
        with self.assertRaisesRegex(ProjectError,'identity differs'):self.check()

    def test_unknown_actual_diameter_basis_pending(self):
        self.alter_basis('overall_diameter_is_actual',None)
        self.assertEqual(self.check()['status'],'pending')

    def test_missing_native_product_metadata_pending(self):
        path=self.case/'selected-model/cables.ifc';model=ifcopenshell.open(str(path));obj=model.by_type('IfcCableSegment')[0]
        ps=model.by_id(element.get_psets(obj)['BSA_CableSelection']['id']);api.run('pset.remove_pset',model,product=obj,pset=ps);model.write(str(path))
        binding=self.case/'selected-model/binding.json';p=json.loads(binding.read_text());p['ifc_sha256']=digest(path);binding.write_text(json.dumps(p),encoding='utf-8')
        self.assertEqual(self.check()['status'],'pending')

    def test_changed_classification_document_rejected(self):
        with (self.case/'source/classification.txt').open('a',encoding='utf-8') as stream:stream.write('changed source')
        with self.assertRaisesRegex(ProjectError,'source path/hash'):self.check()
