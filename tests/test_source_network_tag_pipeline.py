import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bsa import source_network_tag_pipeline as tool
from bsa.cli import digest


class TagPipelineTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder).resolve();base=root/'base';schedule=root/'schedule';base.mkdir();schedule.mkdir()
        (base/'delivery.json').write_text('{}');(schedule/'schedule.json').write_text('{}')
        engine=root/'fictional-engine.txt';engine.write_text('Not executed; rejection controls only')
        return root,base,schedule,engine

    def test_no_complete_placement_blocks_native_and_existing_output_rejects(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            root,base,schedule,engine=self.fixture(folder)
            with patch.object(tool.tags,'study',return_value={'selected':None}),patch.object(tool.native,'run',side_effect=AssertionError('Native must not execute')):
                with self.assertRaisesRegex(ValueError,'native generation blocked'):tool.run(base,schedule,root/'out',engine)
            for out in (base/'nested',root,base):
                with self.assertRaisesRegex(ValueError,'Fresh separate'):tool.run(base,schedule,out,engine)

    def test_missing_artifacts_and_foreign_review_reject_before_replay(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            root,base,schedule,engine=self.fixture(folder);out=root/'out';out.mkdir()
            record=dict(source_delivery=str(base),source_schedule=str(schedule),autocad=str(engine),inputs=tool.inputs(base,schedule,engine),artifacts={})
            def save():(out/'delivery.json').write_text(json.dumps(record))
            save()
            with patch.object(tool.review,'verify',side_effect=AssertionError('Must reject before ancestry replay')):
                with self.assertRaisesRegex(ValueError,'coverage missing'):tool.verify(out)
                names=['annotations/placement.json','annotations/Tagged Network Study.dxf','native/section.dwg','native/sheet.pdf','native/native-verification.json','native/native-reopen/source-export.dxf','review/review.json']
                for name in names:
                    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
                (out/'review/review.json').write_text(json.dumps(dict(study=str(root/'foreign-study'),native_output=str(out/'native'))))
                record['artifacts']={name:digest(out/name) for name in names};save()
                with self.assertRaisesRegex(ValueError,'outside its stages'):tool.verify(out)
