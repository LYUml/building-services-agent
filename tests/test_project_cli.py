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
                '--disable-module-provider','bsa.source-requirements','--moosas-upstream','host-upstream','--moosas-deps','host-deps'])
        self.assertEqual(code,2);self.assertFalse(summary['design_accepted'])
        options=run.call_args.kwargs['execute_options']
        self.assertEqual(options['autocad'],Path('host-autocad.exe'))
        self.assertEqual(options['module_providers'],{'rules':'bsa.electrical-path-rules'})
        self.assertEqual(options['disabled_module_providers'],['bsa.source-requirements'])
        self.assertEqual(options['module_runtime'],dict(upstream=Path('host-upstream'),deps=Path('host-deps')))

    def test_workflow_rejects_duplicate_provider_overrides_before_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=Path(folder)/'result'
            with patch('sys.argv',['bsa','workflow',str(ROOT/'examples/modular-plan.json'),'--out',str(out),
                '--module-provider','spaces=ifcopenshell.box-spaces','--module-provider','spaces=moosas.box-space-exchange']),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):main()
            self.assertFalse(out.exists())

    def test_invalid_provider_selection_rejects_before_execution(self):
        with patch('bsa.engineering_handoff.run') as run,patch('sys.argv',['bsa','handoff','plan','review','--target','target','--out','out','--module-provider','invalid']),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):main()
        run.assert_not_called()

    def test_generated_interpretation_preserves_all_ids_and_cannot_execute_unfilled(self):
        from bsa.engineering_handoff import apply
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);brief=root/'brief.md';brief.write_text('Calculate airflow.\n\nProvide editable drawings.')
            self.invoke(['project-start',brief,'--out',root/'project'])
            plan=root/'project/plan.json';review=plan.with_name('interpretation.json')
            before=plan.read_bytes()
            code,result=self.invoke(['handoff-template',plan,'--out',review])
            self.assertEqual(code,2);self.assertFalse(result['executable'])
            source=json.loads(before);record=json.loads(review.read_text())
            self.assertEqual(set(record['requirement_bindings']),{r['id'] for r in source['requirements']})
            self.assertEqual(set(record['interpretation_notes']),{i['id'] for i in source['unresolved_inputs']})
            self.assertTrue(all(not b['tasks'] and not b['acceptance'] for b in record['requirement_bindings'].values()))
            with self.assertRaises(ValueError):apply(plan,review,plan.with_name('engineering-plan.json'))
            self.assertFalse(plan.with_name('engineering-plan.json').exists())
            self.assertEqual(plan.read_bytes(),before)
            with patch('sys.argv',['bsa','handoff-template',str(plan),'--out',str(review)]),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):main()

    def test_interpretation_template_rejects_unsafe_output_and_existing_engineering_plan(self):
        from bsa.engineering_handoff import template
        from bsa.workflow_draft import draft
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);brief=root/'brief.md';brief.write_text('Review supplied inputs.')
            plan=root/'plan.json';draft(brief,plan)
            with self.assertRaises(ValueError):template(plan,root/'nested/review.json')
            data=json.loads(plan.read_text());data['tasks'][0]=dict(id='interpret-001',kind='electrical',project='electrical.json')
            import shutil
            shutil.copyfile(ROOT/'examples/office-electrical/project.json',root/'electrical.json')
            plan.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'existing engineering tasks'):template(plan,root/'review.json')
            self.assertFalse((root/'review.json').exists())


if __name__=='__main__':unittest.main()
