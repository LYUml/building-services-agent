import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute, passages, verify, validate_plan
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
PYTHON=ROOT/'tools/ifcmcp-runtime/Scripts/python.exe'


@unittest.skipUnless(PYTHON.is_file(),'isolated IFC MCP runtime not installed')
class IFCQueryWorkflowTests(unittest.TestCase):
    def test_inherited_inventory_missing_runtime_and_failed_counts(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);shutil.copyfile(ROOT/'examples/hk-plumbing-pumps/route-model.json',root/'model.json')
            brief=root/'brief.md';brief.write_text('Author a synthetic model, inspect its pump inventory and gate a subsequent query.')
            row=passages(brief)[0]
            required=root/'requirements.json';required.write_text(json.dumps(dict(source='Synthetic inventory contract',minimum_counts={'IfcPump':1,'IfcPipeSegment':2})))
            tasks=[dict(id='model',kind='bim',project='model.json'),
                   dict(id='query',kind='ifc_query',depends_on='model',requirements='requirements.json'),
                   dict(id='after',kind='ifc_query',depends_on='model',requirements='requirements.json',requires_pass=['query'])]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},tasks=tasks,
                      requirements=[dict(id=t['id'],passage=row['id'],quote=row['text'],task=t['id'],acceptance=row['text']) for t in tasks])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            result=execute(path,root/'positive',ifcmcp_python=PYTHON)
            self.assertTrue(result['execution_pass'],result['tasks']);self.assertTrue(verify(root/'positive')['integrity_pass'])
            result=execute(path,root/'missing')
            self.assertEqual(result['tasks']['query']['status'],'pending');self.assertFalse((root/'missing/query').exists())
            required.write_text(json.dumps(dict(source='Synthetic requires two pumps; intentionally unmet',minimum_counts={'IfcPump':2})))
            result=execute(path,root/'negative',ifcmcp_python=PYTHON)
            self.assertEqual(result['tasks']['query']['status'],'fail');self.assertEqual(result['tasks']['after']['status'],'pending')
            self.assertFalse((root/'negative/after').exists());self.assertTrue(verify(root/'negative')['integrity_pass'])
            self.assertFalse(verify(root/'positive')['integrity_pass'])
            tasks[1]['ifc']='model.ifc'
            path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ProjectError,'exactly one'):validate_plan(path)
