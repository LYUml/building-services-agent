import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bsa.epanet import run

ROOT = Path(__file__).resolve().parents[1]


class FailureDiagnosisTests(unittest.TestCase):
    def test_explicit_policy_message_is_distinct_from_generic_worker_failure(self):
        for message, kind in [('ImportError: An Application Control policy has blocked this file.', 'application_control_block'),
                              ('Other unrelated worker error', 'worker_or_result_error')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
                out = Path(tmp)/'run'
                def worker(*args, **kwargs):
                    kwargs['stdout'].write(message.encode('utf-8'))
                    return SimpleNamespace(returncode=1)
                with patch('bsa.epanet.subprocess.run', side_effect=worker), patch('bsa.epanet.importlib.metadata.version', return_value='1.5.0'):
                    result = run(ROOT/'examples/water-loop/project.json', out)
                self.assertEqual(result['engine_failure']['kind'], kind)
                self.assertFalse(result['calculated_checks_pass'])
                self.assertFalse(result['design_accepted'])
                self.assertNotIn('pipes', result)
                self.assertEqual(result['engine_failure']['evidence'], 'worker.log')
                self.assertIn(kind, (out/'report.html').read_text(encoding='utf-8'))
                self.assertEqual(json.loads((out/'water.json').read_text())['engine_failure']['kind'], kind)

    def test_timeout_does_not_become_policy_block_or_design_result(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            with patch('bsa.epanet.subprocess.run', side_effect=subprocess.TimeoutExpired('synthetic worker', 1)), patch('bsa.epanet.importlib.metadata.version', return_value='1.5.0'):
                result = run(ROOT/'examples/water-loop/project.json', Path(tmp)/'run')
            self.assertEqual(result['engine_failure']['kind'], 'timeout')
            self.assertFalse(result['engine_failure']['hydraulic_result_available'])
            self.assertFalse(result['calculated_checks_pass'])
