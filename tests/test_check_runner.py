import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch
from bsa import check_runner as runner

ROOT=Path(__file__).resolve().parents[1]

class CheckRunnerTests(unittest.TestCase):
    def test_watchdog_retains_started_test_and_real_trace_without_result(self):
        self.out.mkdir();runner.write(self.out/'request.json',dict(tests=['tests.test_engine'],test_timeout=1))
        code="""import sys,time,unittest
from unittest.mock import patch
from bsa import check_runner
suite=unittest.TestSuite([unittest.FunctionTestCase(lambda:time.sleep(5))])
with patch.object(unittest.TestLoader,'loadTestsFromNames',return_value=suite):
    sys.exit(check_runner.worker(sys.argv[1]))
"""
        process=subprocess.run([sys.executable,'-X','utf8','-c',code,str(self.out)],cwd=ROOT,capture_output=True,timeout=10)
        self.assertNotEqual(process.returncode,0)
        self.assertIn(b'Timeout',process.stderr);self.assertIn(b'<lambda>',process.stderr)
        self.assertFalse((self.out/'tests.json').exists())
        events=[json.loads(x) for x in (self.out/'progress.jsonl').read_text().splitlines()]
        self.assertEqual([x['event'] for x in events],['loading','started'])
        self.assertTrue(events[-1]['test'])

    def test_invalid_timeout_does_not_create_output(self):
        for value in [0,-1,True,1.5,86401]:
            with self.subTest(value=value),self.assertRaises(ValueError):runner.run(['tests.test_engine'],self.out,test_timeout=value)
        self.assertFalse(self.out.exists())

    def test_whole_repository_mode_uses_fixed_discovery_and_actual_counts(self):
        self.out.mkdir();runner.write(self.out/'request.json',dict(tests=['tests']))
        observed=[];suite=unittest.TestSuite([unittest.FunctionTestCase(lambda:observed.append(True))])
        with patch.object(unittest.TestLoader,'discover',return_value=suite) as discover:
            self.assertEqual(runner.worker(self.out),0)
        discover.assert_called_once_with(str(ROOT/'tests'))
        self.assertEqual(observed,[True])
        self.assertEqual(json.loads((self.out/'tests.json').read_text())['tests_run'],1)
        events=[json.loads(x)['event'] for x in (self.out/'progress.jsonl').read_text().splitlines()]
        self.assertEqual(events,['loading','started','finished','completed'])
        for names in [['tests','tests.test_engine'],['other'],['../tests']]:
            with self.subTest(names=names),self.assertRaises(ValueError):runner.selectors(names)

    def test_discovery_loading_error_precedes_test_bodies(self):
        self.out.mkdir();runner.write(self.out/'request.json',dict(tests=['tests']))
        loader=unittest.TestLoader();loader.errors.append('Controlled discovery import failure')
        observed=[];suite=unittest.TestSuite([unittest.FunctionTestCase(lambda:observed.append(True))])
        with patch('bsa.check_runner.unittest.TestLoader',return_value=loader),patch.object(loader,'discover',return_value=suite):
            self.assertEqual(runner.worker(self.out),1)
        result=json.loads((self.out/'tests.json').read_text())
        self.assertEqual(observed,[]);self.assertEqual(result['tests_run'],0)
        self.assertEqual(result['loading_errors'],['Controlled discovery import failure'])

    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temporary.cleanup)
        self.out=Path(self.temporary.name)/'checks'
        self.name='test_receipt_fixture_'+uuid.uuid4().hex
        self.module=ROOT/'tests'/(self.name+'.py');self.addCleanup(lambda:self.module.unlink(missing_ok=True))

    def execute(self,body):
        self.module.write_text('import unittest\nfrom pathlib import Path\nclass Fixture(unittest.TestCase):\n'+body,encoding='utf-8')
        return runner.run(['tests.'+self.name],self.out)

    def test_process_counts_survive_log_independently_of_terminal(self):
        result=self.execute('    def test_pass(self): self.assertEqual(3*7,21)\n    @unittest.skip("Explicit control")\n    def test_skip(self): pass\n')
        checked=runner.verify(self.out)
        self.assertEqual(result['returncode'],0);self.assertEqual(checked['tests_run'],2)
        self.assertTrue(checked['suite_pass']);self.assertFalse(checked['all_tests_pass'])
        self.assertEqual(checked['passed'],1);self.assertFalse(checked['design_accepted'])
        self.assertTrue((self.out/'started.json').is_file())
        before=(self.out/'tests.json').read_bytes()
        with self.assertRaises(ValueError):runner.worker(self.out)
        self.assertEqual((self.out/'tests.json').read_bytes(),before)

    def test_failing_subtests_are_recorded(self):
        result=self.execute('    def test_fail(self):\n        for value in [1,2]:\n            with self.subTest(value=value): self.assertEqual(value,0)\n')
        checked=runner.verify(self.out)
        self.assertEqual(result['returncode'],1);self.assertFalse(checked['suite_pass'])
        self.assertEqual(result['result']['failures'],2);self.assertEqual(checked['tests_run'],1)

    def test_setup_class_error_and_empty_suite_are_not_green(self):
        result=self.execute('    @classmethod\n    def setUpClass(cls): raise RuntimeError("Declared setup failure")\n    def test_never_runs(self): pass\n')
        self.assertEqual(result['result']['tests_run'],0);self.assertEqual(result['result']['errors'],1)
        self.assertFalse(runner.verify(self.out)['suite_pass'])

    def test_no_executed_pass_is_not_green(self):
        result=self.execute('    @unittest.skip("Only skipped control")\n    def test_skip(self): pass\n')
        self.assertFalse(result['suite_pass']);self.assertEqual(result['returncode'],1)
        self.assertFalse(runner.verify(self.out)['all_tests_pass'])

    def test_source_changed_in_flight_cannot_be_current_pass(self):
        result=self.execute('    def test_change(self):\n        p=Path(__file__);p.write_text(p.read_text()+"\\n# deliberate changed fixture\\n")\n')
        self.assertEqual(result['returncode'],0);self.assertEqual(result['status'],'source_changed')
        self.assertFalse(result['suite_pass'])
        with self.assertRaises(ValueError):runner.verify(self.out)

    def test_log_tampering_or_missing_terminal_receipt_rejects(self):
        self.execute('    def test_pass(self): pass\n')
        path=self.out/'execution.log';path.write_bytes(path.read_bytes()+b'altered')
        with self.assertRaisesRegex(ValueError,'evidence changed'):runner.verify(self.out)
        (self.out/'receipt.json').unlink()
        with self.assertRaises(FileNotFoundError):runner.verify(self.out)

    def test_arbitrary_imports_reject_before_output(self):
        with self.assertRaises(ValueError):runner.run(['os.system'],self.out)
        self.assertFalse(self.out.exists())

    def test_missing_module_prevents_valid_tests_from_starting(self):
        marker=Path(self.temporary.name)/'should-not-exist.txt'
        self.module.write_text('import unittest\nfrom pathlib import Path\nclass Fixture(unittest.TestCase):\n    def test_never_runs(self): Path('+repr(marker.as_posix())+').write_text("ran")\n',encoding='utf-8')
        result=runner.run(['tests.'+self.name,'tests.test_missing_'+uuid.uuid4().hex],self.out)
        checked=runner.verify(self.out)
        self.assertEqual(result['result']['tests_run'],0)
        self.assertEqual(result['result']['errors'],0)
        self.assertEqual(len(result['result']['loading_errors']),1)
        self.assertFalse(marker.exists());self.assertFalse(checked['suite_pass'])
        self.assertEqual(result['returncode'],1)

    def test_broken_fixture_import_is_loading_error_not_executed_case(self):
        result=self.execute('    raise ImportError("Deliberate unavailable fixture")\n    def test_never_runs(self): pass\n')
        self.assertEqual(result['result']['tests_run'],0)
        self.assertEqual(len(result['result']['loading_errors']),1)
        self.assertIn('Deliberate unavailable fixture',result['result']['loading_errors'][0])
        self.assertFalse(runner.verify(self.out)['suite_pass'])

if __name__=='__main__':unittest.main()
