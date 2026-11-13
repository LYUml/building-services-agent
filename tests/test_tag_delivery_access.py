import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bsa import tag_delivery_access as access
from bsa.cli import digest


class TagDeliveryAccessTests(unittest.TestCase):
    def test_pinned_render_paths_and_changed_record_reject(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            out=Path(folder).resolve()/'out';(out/'native').mkdir(parents=True)
            for name in ('section.dwg','sheet.pdf'):(out/'native'/name).write_text('Fictional access control only')
            data=dict(components=2,ancestry_verified=True,native_reopen_verified=True,plot_visual_review='pending',pending=['engineering review'],artifacts={n:digest(out/n) for n in ('native/section.dwg','native/sheet.pdf')})
            (out/'delivery.json').write_text(json.dumps(data))
            with patch.object(access.pipeline,'verify',return_value=data):
                result=access.inspect(out);self.assertTrue(result['integrity_pass']);self.assertFalse(result['design_accepted'])
                self.assertEqual(result['artifacts'][-1]['project_path'],'out/native/sheet.pdf')
            def changed(_):
                (out/'delivery.json').write_text('{}');return data
            with patch.object(access.pipeline,'verify',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during inspection'):access.inspect(out)
            (out/'native/sheet.pdf').write_text('Changed')
            with self.assertRaisesRegex(ValueError,'differs from producer'):access.summary(out,data)

    def test_missing_host_runtime_stops_before_pipeline(self):
        with patch.object(access.pipeline,'run',side_effect=AssertionError('Must not execute')):
            with self.assertRaisesRegex(ValueError,'host AutoCAD'):access.run('base','schedule','out',None)
