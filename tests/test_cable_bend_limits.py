import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.api as api
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.cable_bend_limits import evaluate,prepare,run

ROOT=Path(__file__).resolve().parents[1]


class DeclaredBendLimitTests(unittest.TestCase):
    def setUp(self):
        self.observed=dict(bend_radius_m=.3,envelope_radius_m=.01)
        self.source=dict(path='basis.txt',sha256='a'*64,locator='Synthetic test limits',kind='assumption')
        self.row=dict(product_reference='synthetic-cable-20',diameter_m=.02,diameter_basis='nominal',condition='installed',radius_reference='inside',minimum_radius_m=.295,source='basis')
        self.metadata=dict(ProductReference=self.row['product_reference'],SourceSHA256=self.source['sha256'],InstallationCondition='installed')

    def check(self):return evaluate(self.observed,self.row,self.metadata,self.source)

    def test_inside_limit_not_compared_to_centreline(self):
        result=self.check();self.assertEqual(result['status'],'fail')
        self.assertAlmostEqual(result['evaluated_radius_m'],.29)
        self.row['radius_reference']='centreline';self.assertEqual(self.check()['status'],'pass')

    def test_unknown_radius_reference_does_not_pass(self):
        self.row['radius_reference']='unknown';result=self.check()
        self.assertEqual(result['status'],'pending');self.assertIsNone(result['numeric_radius_comparison'])

    def test_installed_limit_cannot_clear_pulling_condition(self):
        self.row['minimum_radius_m']=.28;self.metadata['InstallationCondition']='during_installation_under_tension'
        self.assertEqual(self.check()['status'],'fail')

    def test_missing_native_product_and_condition_remain_pending(self):
        self.metadata={};self.row['minimum_radius_m']=.28
        self.assertEqual(self.check()['status'],'pending')

    def test_nominal_diameter_mismatch_and_source_change_fail(self):
        self.row['diameter_m']=.0151;self.assertEqual(self.check()['status'],'fail')
        self.row['diameter_m']=.02;self.metadata['SourceSHA256']='b'*64
        self.assertEqual(self.check()['status'],'fail')

    def test_maximum_diameter_uses_conservative_envelope(self):
        self.row.update(diameter_basis='maximum',diameter_m=.019,minimum_radius_m=.28)
        self.assertEqual(self.check()['status'],'pass')
        self.row['diameter_m']=.021;self.assertEqual(self.check()['status'],'fail')


class NativeBendLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        source=ROOT/'examples/three-phase-bend'
        cls.project=source/'project.json'
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(cls.project,source/'geometry.json',cls.root/'fixture','mixed-revolution')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.folder=self.root/self._testMethodName;shutil.copytree(self.root/'fixture',self.folder)
        self.ifc=self.folder/'cables.ifc';self.binding=self.folder/'binding.json'
        text=self.folder/'limits.txt';text.write_text('Synthetic product synthetic-cable-20: nominal diameter 0.02 m; installed inside radius minimum 0.28 m. Not a real product, code or selected installation.',encoding='utf-8')
        self.source=dict(path='limits.txt',sha256=digest(text),locator='Synthetic dimensional and installed-inside-radius paragraph',kind='assumption')
        self.basis=self.folder/'limits.json'
        p=dict(version=1,sources=dict(basis=self.source),bends=dict(feeder=dict(product_reference='synthetic-cable-20',diameter_m=.02,diameter_basis='nominal',condition='installed',radius_reference='inside',minimum_radius_m=.28,source='basis')))
        self.basis.write_text(json.dumps(p),encoding='utf-8')

    def attach(self):
        m=ifcopenshell.open(str(self.ifc));b=json.loads(self.binding.read_text())
        obj=m.by_guid(b['lines']['feeder']['element_guid'])
        ps=api.run('pset.add_pset',m,product=obj,name='BSA_CableSelection')
        api.run('pset.edit_pset',m,pset=ps,properties=dict(ProductReference='synthetic-cable-20',SourceSHA256=self.source['sha256'],InstallationCondition='installed'))
        m.write(str(self.ifc));b['ifc_sha256']=digest(self.ifc);self.binding.write_text(json.dumps(b),encoding='utf-8')

    def test_actual_native_identity_and_inside_radius_check(self):
        self.attach();before=digest(self.ifc)
        result=run(self.project,self.ifc,self.binding,self.basis,self.folder/'result')
        self.assertEqual(result['status'],'pass');self.assertFalse(result['manufacturer_selection_verified'])
        self.assertFalse(result['design_accepted']);self.assertEqual(digest(self.ifc),before)
        self.assertAlmostEqual(result['bends'][0]['inside_radius_m'],.29)

    def test_native_missing_selection_metadata_does_not_pass(self):
        result=run(self.project,self.ifc,self.binding,self.basis,self.folder/'result')
        self.assertEqual(result['status'],'pending')

    def test_source_tamper_rejected(self):
        with (self.folder/'limits.txt').open('a') as f:f.write('changed')
        with self.assertRaisesRegex(ProjectError,'source path/hash'):prepare(self.basis)

    def test_omitted_supported_bend_rejected(self):
        p=json.loads(self.basis.read_text());p['bends']={};self.basis.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'exact selected-system'):run(self.project,self.ifc,self.binding,self.basis,self.folder/'result')
