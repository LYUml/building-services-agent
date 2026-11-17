import contextlib,io,tomllib,unittest
from pathlib import Path
from unittest.mock import patch
from bsa.cli import main
from bsa.cli_errors import EXTRAS,missing_dependency

ROOT=Path(__file__).resolve().parents[1]

class MissingDependencyErrors(unittest.TestCase):
    def test_worker_retains_structured_missing_profile_failure(self):
        import json
        from bsa import mcp_worker
        request=json.dumps(dict(operation='bsa.reference_library.catalogue',args=[],kwargs={}))
        output=io.StringIO()
        with patch('sys.stdin',io.StringIO(request)),contextlib.redirect_stdout(output),patch('bsa.mcp_worker.resolve',side_effect=ModuleNotFoundError('Missing rectpack',name='rectpack')):
            code=mcp_worker.main()
        result=json.loads(output.getvalue());self.assertEqual(code,2);self.assertFalse(result['ok'])
        self.assertEqual(result['error_kind'],'missing_dependency');self.assertEqual(result['suggested_extra'],'drawing-layout')

    def test_hints_are_real_declared_profiles_and_nested_errors_are_not_guessed(self):
        declared=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['optional-dependencies']
        self.assertTrue(set(EXTRAS.values())<=set(declared))
        result=missing_dependency(ModuleNotFoundError('Missing rectpack',name='rectpack'))
        self.assertEqual(result['suggested_extra'],'drawing-layout')
        self.assertIn('python -m pip install -e ".[drawing-layout]"',result['message'])
        unknown=missing_dependency(ModuleNotFoundError('Missing nested module',name='rectpack.unknown'))
        self.assertIsNone(unknown['suggested_extra']);self.assertNotIn('pip install',unknown['message'])

    def test_cli_has_actionable_exit2_without_traceback_or_execution_claim(self):
        stderr=io.StringIO()
        with patch('bsa.drawing_access.inspect',side_effect=ModuleNotFoundError('Missing rectpack',name='rectpack')),patch('sys.argv',['bsa','drawing','inspect','input.json','--out','result']),contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:main()
        self.assertEqual(caught.exception.code,2);self.assertIn('drawing-layout',stderr.getvalue())
        self.assertNotIn('Traceback',stderr.getvalue())

if __name__=='__main__':unittest.main()
