import contextlib
import io
import json
import os
import unittest
from unittest.mock import Mock,patch

from bsa.verification_scope import operation_scope,replay_json,MAX_BYTES


class VerificationScopeTests(unittest.TestCase):
    def test_no_scope_and_disabled_scope_always_replay(self):
        produce=Mock(return_value={'value':1})
        replay_json('same',produce);replay_json('same',produce)
        with operation_scope(enabled=False):
            replay_json('same',produce);replay_json('same',produce)
        self.assertEqual(produce.call_count,4)

    def test_scopes_are_isolated_and_results_defensively_copied(self):
        produce=Mock(return_value={'values':[1]})
        with operation_scope():
            replay_json('same',produce)['values'].append(2)
            self.assertEqual(replay_json('same',produce),{'values':[1]})
            with operation_scope():replay_json('same',produce)
            replay_json('same',produce)
        with operation_scope():replay_json('same',produce)
        self.assertEqual(produce.call_count,3)

    def test_keys_failures_size_and_entry_limits_preserve_original_execution(self):
        produce=Mock(return_value={'value':1})
        with operation_scope():
            for i in range(5):replay_json(i,produce)
            replay_json(0,produce)
            self.assertEqual(produce.call_count,6)
            big=Mock(return_value={'text':'x'*MAX_BYTES})
            replay_json('large',big);replay_json('large',big)
            self.assertEqual(big.call_count,2)
            failed=Mock(side_effect=ValueError('reader failed'))
            for _ in range(2):
                with self.assertRaises(ValueError):replay_json('failure',failed)
            self.assertEqual(failed.call_count,2)
        replay_json(0,produce)
        self.assertEqual(produce.call_count,7)

    def test_worker_creates_and_clears_scope_and_host_can_disable(self):
        from bsa import mcp_worker
        request=json.dumps(dict(operation='bsa.reference_library.catalogue',args=[],kwargs={}))
        produce=Mock(return_value={'value':1})
        def operation():
            a=replay_json('same',produce);b=replay_json('same',produce)
            return [a,b]
        for disabled,expected in [('0',1),('1',2)]:
            produce.reset_mock()
            with patch.dict(os.environ,{'BSA_DISABLE_AUDIT_MEMO':disabled}),patch.object(mcp_worker,'resolve',return_value=operation),patch('sys.stdin',io.StringIO(request)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mcp_worker.main(),0)
            self.assertEqual(produce.call_count,expected)
            replay_json('same',produce)
            self.assertEqual(produce.call_count,expected+1)
