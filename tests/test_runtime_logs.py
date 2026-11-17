from pathlib import Path
import tempfile
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bsa.runtime_logs import inspect_log,CHUNK_BYTES

ROOT=Path(__file__).resolve().parents[1]


class RuntimeLogTests(unittest.TestCase):
    def test_worker_failure_exposes_retained_bounded_trace_without_hydraulics(self):
        from bsa.epanet import run
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root=Path(directory);project=ROOT/'examples/water-loop/project.json'
            def failed(*args,**kwargs):
                kwargs['stdout'].write(b'x'*20000+b'\nModuleNotFoundError: controlled test dependency\n')
                return SimpleNamespace(returncode=1)
            with patch('bsa.epanet.subprocess.run',side_effect=failed),patch('bsa.epanet.importlib.metadata.version',return_value='1.5.0'):
                result=run(project,root/'execution')
            failure=result['engine_failure'];self.assertFalse(result['calculated_checks_pass'])
            self.assertFalse(failure['hydraulic_result_available']);self.assertEqual(failure['kind'],'worker_or_result_error')
            self.assertTrue(failure['diagnostics']['truncated'])
            self.assertIn('ModuleNotFoundError',failure['diagnostics']['tail'])
            self.assertLessEqual(len(failure['diagnostics']['tail'].encode()),8192)
            saved=json.loads((root/'execution/water.json').read_text())
            self.assertEqual(saved['engine_failure'],failure)
            self.assertFalse((root/'execution/raw.json').exists())

    def test_policy_outside_tail_and_across_chunks_is_retained(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            path=Path(directory)/'worker.log'
            data=b'a'*(CHUNK_BYTES-10)+b'An Application Control Policy blocked it\n'+b'b'*20000+b'\nTraceback: actual worker failure\xff'
            path.write_bytes(data)
            result=inspect_log(path,tail_limit=256)
            self.assertTrue(result['application_control_policy'])
            self.assertEqual(result['tail'],data[-256:].decode('utf-8',errors='replace'))
            self.assertEqual(result['bytes'],len(data));self.assertTrue(result['truncated'])
            self.assertEqual(path.read_bytes(),data)

    def test_empty_and_nonpolicy_log_do_not_invent_a_policy_block(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            path=Path(directory)/'worker.log';path.write_bytes(b'')
            self.assertEqual(inspect_log(path),dict(tail='',bytes=0,truncated=False,application_control_policy=False))
            path.write_bytes(b'ModuleNotFoundError: required_dependency')
            result=inspect_log(path);self.assertFalse(result['application_control_policy']);self.assertFalse(result['truncated'])
            for value in [0,True,65537]:
                with self.subTest(value=value),self.assertRaises(ValueError):inspect_log(path,tail_limit=value)


if __name__=='__main__':unittest.main()
