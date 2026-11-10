import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsa.hvac_package import run
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class PackageSystemPathTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.plan=self.root/'plan.json';self.plan.write_text('{}')
        self.font=self.root/'font.ttf';self.font.write_bytes(b'Unit font placeholder;PDF renderer is mocked')
        self.source=self.root/'source.txt';self.source.write_text('Original source control')

    def execute(self,plan,out,**kwargs):
        out.mkdir();r=dict(tasks={'native':dict(kind='duct_sheet_native',status='pass',scope='Unit stage control only')})
        (out/'workflow.json').write_text(json.dumps(r));return r

    def study(self,plan,workflow,native,out):
        out.mkdir();(out/'index.html').write_text('Unit stage placeholder')
        r=dict(inputs={str(self.source):digest(self.source)},section_count=1,outlet_path_count=1,status='pending',design_accepted=False)
        (out/'system-paths.json').write_text(json.dumps(r));return r

    def controlled(self,out,*,stage=None,report=None,native='native'):
        # Stage plumbing only;no native CAD/PDF or engineering evidence is mocked as real.
        with patch('bsa.hvac_package.validate_plan',return_value=(dict(tasks=[dict(id='native',kind='duct_sheet_native')]),{self.plan})),patch('bsa.hvac_package.execute',side_effect=self.execute),patch('bsa.hvac_package.diagnose',return_value={}),patch('bsa.hvac_package.template'),patch('bsa.hvac_package.verify',return_value=dict(integrity_pass=True)),patch('bsa.duct_system_paths.run',side_effect=stage or self.study) as study,patch('bsa.hvac_report.run',side_effect=report or (lambda *a,**kw:dict(scope='Unit report control'))),patch('bsa.hvac_report_pdf.run',return_value=dict(scope='Unit PDF control;no PDF authored')):
            result=run(self.plan,out,font=self.font,system_paths_native_task=native)
            return result,study.call_args_list

    def test_handoff_index_hashes_and_omitted_configuration(self):
        out=self.root/'package';r,calls=self.controlled(out)
        self.assertEqual(r['system_paths_native_task'],'native');self.assertEqual(r['status'],'review_required')
        self.assertFalse(r['design_accepted']);self.assertEqual(r['stages']['system_paths']['status'],'pending')
        self.assertEqual(calls[0].args,(self.plan,out/'workflow','native',out/'system-paths'))
        self.assertEqual(r['artifact_hashes'][str(Path('system-paths/index.html'))],digest(out/'system-paths/index.html'))
        text=(out/'index.html').read_text();self.assertIn('system-paths/index.html',text);self.assertIn('Nominal untrimmed',text)
        omitted,calls=self.controlled(self.root/'omitted',native=None)
        self.assertIsNone(omitted['system_paths_native_task']);self.assertFalse(calls);self.assertNotIn('system_paths',omitted['stages'])

    def test_invalid_task_and_stage_failure_remain_explicit(self):
        out=self.root/'invalid'
        with self.assertRaisesRegex(ValueError,'declared native sheet'):self.controlled(out,native='unknown')
        self.assertFalse(out.exists())
        def failed(*a):raise ValueError('Controlled native correspondence failure')
        out=self.root/'failed';r,_=self.controlled(out,stage=failed)
        self.assertEqual(r['status'],'incomplete');self.assertIn('system_paths',r['stage_errors'])
        self.assertNotIn('system_paths',r['stages']);self.assertNotIn('system-paths/index.html',(out/'index.html').read_text())

    def test_source_mutation_during_later_report_blocks_package(self):
        def changed(*a,**kw):self.source.write_text('Changed during later report');return dict(scope='Unit report mutation control')
        out=self.root/'mutated'
        with self.assertRaisesRegex(ValueError,'System path source or method changed'):self.controlled(out,report=changed)
        self.assertFalse((out/'package.json').exists())
