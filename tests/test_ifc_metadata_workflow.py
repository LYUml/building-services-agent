import json
from pathlib import Path
import shutil
import tempfile
import unittest
from bsa.cli import digest
from bsa.workflow import execute,passages,verify

ROOT=Path(__file__).resolve().parents[1]
PYTHON=ROOT/'tools/ifcmcp-runtime/Scripts/python.exe'


@unittest.skipUnless(PYTHON.is_file(),'isolated MCP runtime not installed')
class MetadataWorkflowTests(unittest.TestCase):
    def test_saved_metadata_to_fresh_query_and_duplicate_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            for src,dst in [('examples/hk-plumbing-pumps/route-model.json','model.json'),
                            ('examples/ifcmcp/pump-properties.json','patch.json'),
                            ('examples/ifcmcp/inventory-requirements.json','requirements.json')]:
                shutil.copyfile(ROOT/src,root/dst)
            brief=root/'brief.md';brief.write_text('Synthetic model: add sourced pump review metadata and query the saved revised model.')
            row=passages(brief)[0]
            tasks=[dict(id='model',kind='bim',project='model.json'),
                   dict(id='old_inventory',kind='ifc_query',depends_on='model',requirements='requirements.json'),
                   dict(id='metadata',kind='ifc_metadata',depends_on='model',patch='patch.json',requires_pass=['old_inventory']),
                   dict(id='inventory',kind='ifc_query',depends_on='metadata',requirements='requirements.json',refresh_inventory=True)]
            def plan():
                p=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={row['id']:'requirement'},tasks=tasks,
                       requirements=[dict(id=t['id'],passage=row['id'],quote=row['text'],task=t['id'],acceptance=row['text']) for t in tasks])
                path=root/'plan.json';path.write_text(json.dumps(p));return path
            result=execute(plan(),root/'positive',ifcmcp_python=PYTHON)
            self.assertTrue(result['execution_pass'],result['tasks']);self.assertTrue(verify(root/'positive')['integrity_pass'])
            edited=root/'positive/metadata/native/model.ifc'
            report=json.loads((root/'positive/inventory/ifc-query.json').read_text())
            self.assertEqual(report['inputs'][str(edited)],digest(edited))
            tasks[2].pop('requires_pass')
            tasks.insert(3,dict(id='duplicate',kind='ifc_metadata',depends_on='metadata',patch='patch.json'))
            tasks[-1]['depends_on']='duplicate'
            result=execute(plan(),root/'negative',ifcmcp_python=PYTHON)
            self.assertEqual(result['tasks']['duplicate']['status'],'fail')
            self.assertEqual(result['tasks']['inventory']['status'],'pending')
            self.assertFalse((root/'negative/inventory').exists())
            self.assertTrue(verify(root/'negative')['integrity_pass'])
