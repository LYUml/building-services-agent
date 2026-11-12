import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import main

ROOT=Path(__file__).resolve().parents[1]


class ProjectCLITests(unittest.TestCase):
    def invoke(self,args):
        with patch('sys.argv',['bsa',*map(str,args)]),contextlib.redirect_stdout(io.StringIO()) as output:
            code=main()
        return code,json.loads(output.getvalue())

    def test_actual_intake_keeps_reference_context_and_pending_interpretation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);brief=root/'brief.md';reference=root/'reference.md'
            brief.write_text('Calculate supply airflow.');reference.write_text('General background only.')
            code,result=self.invoke(['project-start',brief,'--reference',reference,'--out',root/'project'])
            self.assertEqual(code,2);self.assertEqual(result['status'],'needs_interpretation')
            self.assertFalse(result['design_accepted'])
            plan=json.loads((root/'project'/result['effective_plan']).read_text())
            self.assertEqual(len(plan['requirements']),1)
            self.assertEqual(plan['passage_dispositions']['D002:P001'],'context')
            self.assertFalse((root/'project/workflow').exists())

    def test_explicit_host_runtime_and_provider_choices_reach_existing_handoff(self):
        result=dict(status='requirements_unavailable',stages={},stage_errors={},design_accepted=False)
        with patch('bsa.engineering_handoff.run',return_value=result) as run:
            code,summary=self.invoke(['handoff','plan.json','interpretation.json','--target','target.json','--out','new-run',
                '--autocad','host-autocad.exe','--module-provider','rules=bsa.electrical-path-rules',
                '--disable-module-provider','bsa.source-requirements'])
        self.assertEqual(code,2);self.assertFalse(summary['design_accepted'])
        options=run.call_args.kwargs['execute_options']
        self.assertEqual(options['autocad'],Path('host-autocad.exe'))
        self.assertEqual(options['module_providers'],{'rules':'bsa.electrical-path-rules'})
        self.assertEqual(options['disabled_module_providers'],['bsa.source-requirements'])

    def test_invalid_provider_selection_rejects_before_execution(self):
        with patch('bsa.engineering_handoff.run') as run,patch('sys.argv',['bsa','handoff','plan','review','--target','target','--out','out','--module-provider','invalid']),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):main()
        run.assert_not_called()


if __name__=='__main__':unittest.main()
