import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.regulations import evaluate
from bsa.three_phase_bridge import run as study_run
from bsa.three_phase_regulations import run,unbalance

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'regulations/hk/phase-balance-2026.11.10/pack.json'
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')
SOURCES=os.environ.get('BSA_TEST_HK_SOURCES')


class UnbalanceMathTests(unittest.TestCase):
    def test_definition_uses_maximum_deviation_not_phase_range(self):
        self.assertAlmostEqual(unbalance([110,100,90]),10)
        self.assertAlmostEqual(unbalance([120,100,80]),20)
        self.assertAlmostEqual(unbalance([120,120,60]),40)
        self.assertAlmostEqual(unbalance([100,100,100]),0)
        self.assertIsNone(unbalance([0,0,0]))
        for values in ([True,1,2],[-1,1,2],[1,2],[1,float('nan'),2]):
            with self.assertRaises(ProjectError):unbalance(values)


@unittest.skipUnless(PYTHON and SOURCES,'requires explicit isolated runtime and official source cache')
class ThreePhaseRegulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        shutil.copytree(ROOT/'examples/three-phase-network',cls.root/'source')
        cls.project=cls.root/'source/project.json';cls.study=cls.root/'study'
        study_run(cls.project,cls.study,Path(PYTHON))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.case=tempfile.TemporaryDirectory(dir=self.root);self.addCleanup(self.case.cleanup)
        self.folder=Path(self.case.name)
        self.basis=json.loads((ROOT/'examples/three-phase-network/hk-basis.json').read_text(encoding='utf-8-sig'))
        self.cache=self.folder/'official';self.cache.mkdir()
        shutil.copyfile(Path(SOURCES)/'emsd-bec-2024.pdf',self.cache/'emsd-bec-2024.pdf')
        self.path=self.folder/'basis.json';self.save()

    def save(self):
        source=self.folder/'scenario.json'
        source.write_text(json.dumps(dict(scope='Synthetic regulatory test only; no actual equipment',circuits=self.basis['circuits'])),encoding='utf-8')
        self.basis['sources']['scenario'].update(path=source.name,sha256=digest(source),locator='Complete synthetic circuit declarations')
        self.path.write_text(json.dumps(self.basis),encoding='utf-8')

    def check(self,name='result',project=None,study=None):
        return run(project or self.project,study or self.study,self.path,PACK,self.cache,self.folder/name)

    def test_actual_study_feeder_pass_and_branch_below_protection_threshold(self):
        result=self.check()
        self.assertEqual(result['status'],'pass');self.assertFalse(result['design_accepted'])
        self.assertEqual(result['regulatory_compliance'],'not_established')
        checks=result['circuit_checks']
        self.assertEqual(checks['feeder']['checks'][0]['status'],'pass')
        self.assertEqual(checks['branch']['checks'][0]['status'],'not_applicable')
        self.assertGreater(checks['branch']['computed_unbalance_percent'],10)

    def test_rating_boundary_and_exceeded_current_balance(self):
        self.basis['circuits']['feeder']['protective_device_rating']['value']=399.999;self.save()
        result=self.check('below')
        self.assertFalse(result['supported_checks_pass'])
        self.assertTrue(all(r['checks'][0]['status']=='not_applicable' for r in result['circuit_checks'].values()))
        self.basis['circuits']['feeder']['protective_device_rating']['value']=400
        self.basis['circuits']['branch']['protective_device_rating']['value']=400;self.save()
        result=self.check('exceeded')
        self.assertEqual(result['status'],'pending')
        self.assertEqual(result['circuit_checks']['branch']['checks'][0]['status'],'review_required')

    def test_missing_rating_or_false_rms_basis_stays_pending(self):
        original=copy.deepcopy(self.basis)
        del self.basis['circuits']['feeder']['protective_device_rating'];self.save()
        result=self.check('missing')
        self.assertEqual(result['circuit_checks']['feeder']['checks'][0]['status'],'pending')
        self.basis=original
        self.basis['circuits']['feeder']['facts']['sinusoidal_design_model_applicable']['value']=False;self.save()
        result=self.check('not-rms')
        self.assertEqual(result['status'],'pending')
        self.assertIn('sinusoidal_design_model_applicable',result['circuit_checks']['feeder']['model_prerequisites_pending'])

    def test_rule_boundary_and_official_source_tampering(self):
        result=self.check('base')
        derived=json.loads((self.folder/'base/derived-projects.json').read_text())['feeder']
        pack=json.loads(PACK.read_text())
        derived['facts']['phase_current_unbalance_percent']['value']=10
        self.assertEqual(evaluate(pack,derived,self.cache)['checks'][0]['status'],'pass')
        derived['facts']['phase_current_unbalance_percent']['value']=10.000001
        self.assertEqual(evaluate(pack,derived,self.cache)['checks'][0]['status'],'review_required')
        (self.cache/'emsd-bec-2024.pdf').write_bytes(b'changed official source')
        self.assertEqual(self.check('bad-source')['status'],'pending')

    def test_override_current_values_is_rejected(self):
        self.basis['circuits']['feeder']['phase_current_a']=[100,100,100];self.save()
        with self.assertRaisesRegex(ProjectError,'cannot be overridden'):self.check()

    def test_pack_defined_scope_fact_names_do_not_require_engine_changes(self):
        pack=json.loads(PACK.read_text());pack['id']='hk-phase-balance-interface-test'
        pack['rules'][0]['applicability'][0]['fact']='electrical_installation_in_scope'
        self.basis['rule_pack']=pack['id']
        for circuit in self.basis['circuits'].values():
            circuit['facts']['electrical_installation_in_scope']=circuit['facts'].pop('bec_electrical_scope_confirmed')
        self.save();path=self.folder/'interface-pack.json';path.write_text(json.dumps(pack),encoding='utf-8')
        result=run(self.project,self.study,self.path,path,self.cache,self.folder/'result')
        self.assertEqual(result['status'],'pass')

    def test_regulatory_pass_does_not_clear_failed_study_target(self):
        source=self.folder/'network';shutil.copytree(ROOT/'examples/three-phase-network',source)
        p=json.loads((source/'project.json').read_text(encoding='utf-8-sig'))
        file=source/'basis.md';file.write_text(file.read_text(encoding='utf-8').replace('100 A','1 A'),encoding='utf-8')
        for line in p['lines']:line['max_current_a']=1
        for record in p['sources'].values():record['sha256']=digest(file)
        (source/'project.json').write_text(json.dumps(p),encoding='utf-8')
        study_run(source/'project.json',self.folder/'failed-study',Path(PYTHON))
        result=self.check(project=source/'project.json',study=self.folder/'failed-study')
        self.assertTrue(result['supported_checks_pass']);self.assertEqual(result['status'],'fail')


if __name__=='__main__':unittest.main()
