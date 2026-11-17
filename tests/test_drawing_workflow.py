import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa.workflow import execute,verify,validate_plan
from bsa.native_cad import DEFAULT_EXE
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]

class DrawingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        data=json.loads((ROOT/'examples/drawing-workflow-plan.json').read_text());data['tasks'][0]['project']='document.json';data['brief']='brief.md'
        self.plan=self.root/'plan.json';self.plan.write_text(json.dumps(data))
        (self.root/'brief.md').write_bytes((ROOT/'examples/drawing-workflow/brief.md').read_bytes())
        (self.root/'document.json').write_bytes((ROOT/'examples/drawing-document.json').read_bytes())

    def test_missing_runtime_remains_pending_without_partial_native(self):
        out=self.root/'missing';result=execute(self.plan,out)
        self.assertEqual(result['tasks']['sheet']['status'],'pending');self.assertFalse((out/'sheet').exists())
        self.assertFalse(result['design_accepted']);self.assertTrue(verify(out)['integrity_pass'])
        from bsa.workflow_status import diagnose
        from bsa.delivery import template
        self.assertFalse(diagnose(self.plan,out)['execution_pass'])
        review=template(self.plan,out,self.root/'review.json')
        self.assertEqual(len(review['requirements']),2)
        self.assertTrue(all(r['status']=='pending' for r in review['requirements']))

    def test_document_cannot_choose_runtime_or_another_schema(self):
        data=json.loads(self.plan.read_text());data['tasks'][0]['autocad']='document.exe';self.plan.write_text(json.dumps(data))
        with self.assertRaises(ValueError):validate_plan(self.plan)
        data['tasks'][0].pop('autocad');self.plan.write_text(json.dumps(data))
        source=self.root/'document.json';doc=json.loads(source.read_text());doc['schema']='bsa.drawing-layout/1';source.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):validate_plan(self.plan)

    @unittest.skipUnless(DEFAULT_EXE.is_file(),'Host executable used for hash; no CAD execution')
    def test_false_native_report_cannot_release_review(self):
        out=self.root/'false'
        with patch('bsa.drawing_access.run',return_value=dict(integrity_pass=True,native_reopen_pass=False)),patch('bsa.drawing_access.inspect',return_value=dict(integrity_pass=True,native_reopen_pass=False)):
            result=execute(self.plan,out,autocad=DEFAULT_EXE)
        self.assertEqual(result['tasks']['sheet']['status'],'fail');self.assertEqual(result['tasks']['review']['status'],'pending')
        self.assertIn(str(DEFAULT_EXE.resolve()),result['runtime_inputs'])

    def test_source_and_method_pins_include_document_adapters(self):
        _,inputs=validate_plan(self.plan)
        for name in ['drawing_document.py','drawing_access.py','cad_sheet.py','native_cad.py']:
            self.assertIn(ROOT/'src/bsa'/name,inputs)
        self.assertIn(self.root/'document.json',inputs)

    @unittest.skipUnless(DEFAULT_EXE.is_file(),'Requires actual AutoCAD save/reopen')
    def test_native_roundtrip_and_rehashed_geometry_forgery(self):
        import ezdxf
        out=self.root/'native';result=execute(self.plan,out,autocad=DEFAULT_EXE)
        self.assertEqual(result['tasks']['sheet']['status'],'pass');self.assertTrue(verify(out)['integrity_pass'])
        self.assertEqual(result['tasks']['review']['status'],'pending');self.assertFalse(result['design_accepted'])
        path=out/'sheet/Drawing.dxf';doc=ezdxf.readfile(path);doc.modelspace().query('CIRCLE')[0].dxf.radius+=1;doc.saveas(path)
        receipt=out/'sheet/drawing-result.json';r=json.loads(receipt.read_text());r['dxf_sha256']=digest(path);receipt.write_text(json.dumps(r))
        report=out/'workflow.json';r=json.loads(report.read_text())
        for p in [path,receipt]:r['artifact_hashes'][p.relative_to(out).as_posix()]=digest(p)
        report.write_text(json.dumps(r))
        checked=verify(out);self.assertFalse(checked['integrity_pass'])
        self.assertTrue(any('general drawing evidence invalid' in issue for issue in checked['issues']))

if __name__=='__main__':unittest.main()
