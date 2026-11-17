import asyncio,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from bsa import workspace
from bsa.cli import run
from bsa.workflow import intake,execute

ROOT=Path(__file__).resolve().parents[1]

class WorkspaceWriteGuards(unittest.TestCase):
    def test_delivery_outputs_reject_before_reading_or_executing(self):
        from bsa import delivery
        from bsa.cli import main
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
            out=Path(directory)/'review.json';plan=ROOT/'examples/drawing-workflow-plan.json'
            with patch('bsa.delivery.context') as context:
                with self.assertRaisesRegex(ValueError,'workspace'):delivery.template(plan,ROOT/'runs/missing',out)
                with self.assertRaisesRegex(ValueError,'workspace'):delivery.run(plan,ROOT/'runs/missing',ROOT/'runs/review.json',out)
                context.assert_not_called()
            import contextlib,io
            with patch('bsa.workflow.execute') as execute_mock,patch('sys.argv',['bsa','workflow',str(plan),'--out',str(ROOT/'runs/uncreated-review-control'),'--review',str(out)]),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):main()
                execute_mock.assert_not_called()
            self.assertFalse(out.exists())
    def test_unselected_external_writes_reject_before_output(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
            root=Path(directory);project=root/'project.json';project.write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
            brief=root/'brief.md';brief.write_text('Retain source requirements.')
            for name,operation in [('electrical',lambda out:run(project,out)),('intake',lambda out:intake(brief,out)),('workflow',lambda out:execute(root/'unread-plan.json',out))]:
                output=root/name
                with self.subTest(name=name),self.assertRaisesRegex(ValueError,'selected'):
                    operation(output)
                self.assertFalse(output.exists())

    def test_explicit_external_electrical_and_intake_preserve_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);project=root/'project.json';project.write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes());before=project.read_bytes()
            brief=root/'brief.md';brief.write_text('Retain source requirements.')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(root)}):
                run(project,root/'electrical');intake(brief,root/'intake.json')
                self.assertTrue((root/'electrical/manifest.json').is_file());self.assertEqual(project.read_bytes(),before)

    def test_history_selection_and_ancestor_coverage_cannot_write(self):
        with tempfile.TemporaryDirectory() as directory:
            parent=Path(directory).resolve();agent=parent/'agent';agent.mkdir();history=parent/'polyu_bse3124';history.mkdir()
            project=agent/'project.json';project.write_bytes((ROOT/'examples/office-electrical/project.json').read_bytes())
            with patch.object(workspace,'ROOT',agent):
                for chosen in [history,history/'child']:
                    if chosen!=history:chosen.mkdir()
                    with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(chosen)}):
                        with self.assertRaisesRegex(ValueError,'read-only'):workspace.project_root()
                with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(parent)}):
                    self.assertFalse(workspace.allowed(history/'new.json'));self.assertFalse(workspace.intake_output(history/'new'))
                    self.assertTrue(workspace.allowed(project))
                    with self.assertRaises(ValueError):run(project,history/'output')
                    self.assertFalse((history/'output').exists())

    def test_actual_history_path_is_only_queried_not_modified(self):
        historical=workspace.ROOT.parent/'polyu_bse3124'
        with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(workspace.ROOT.parent)}):
            self.assertFalse(workspace.allowed(historical/'uncreated-scope-control'))
            self.assertFalse(workspace.intake_output(historical/'uncreated-scope-control'))
        with tempfile.TemporaryDirectory() as directory,patch.object(workspace,'ROOT',Path(directory)/'relocated-agent'):
            self.assertTrue(workspace.protected(Path.home()/'Desktop'/'polyu_bse3124'/'uncreated-scope-control'))

class MCPHistoryGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_checkout_default_server_initializes_only_runs(self):
        from bsa.mcp_server import create_server
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()/'agent';root.mkdir()
            with patch.object(workspace,'ROOT',root),patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                server=create_server();self.assertEqual(len(await server.list_tools()),40)
                self.assertTrue((root/'runs').is_dir());self.assertFalse((root/'.codex').exists())

    async def test_json_writer_rejects_synthetic_history_under_broad_root(self):
        from bsa.mcp_server import create_server
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();agent=root/'agent';agent.mkdir();history=root/'polyu_bse3124';history.mkdir()
            with patch.object(workspace,'ROOT',agent),patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(root)}):
                server=create_server()
                with self.assertRaisesRegex(Exception,'read-only'):
                    await server.call_tool('bsa_save_json',dict(path='polyu_bse3124/blocked.json',data={'source':'Synthetic control'}))
                self.assertFalse((history/'blocked.json').exists())
                await server.call_tool('bsa_save_json',dict(path='active/project.json',data={'source':'Explicit selected sandbox'}))
                self.assertTrue((root/'active/project.json').is_file())

if __name__=='__main__':unittest.main()
