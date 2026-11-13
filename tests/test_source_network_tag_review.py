import json
import tempfile
import unittest
from pathlib import Path
import ezdxf
from bsa.source_network_tag_review import native_stage
from bsa.cli import digest
from bsa.engine import ProjectError


class NativeTagReviewTests(unittest.TestCase):
    def test_rehashed_changed_export_still_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();out=root/'native';out.mkdir();(out/'native-reopen').mkdir()
            doc=ezdxf.new();doc.header['$INSUNITS']=6;line=doc.modelspace().add_line((0,0),(1,0))
            source=root/'source.dxf';doc.saveas(source);doc.saveas(out/'input.dxf')
            line.dxf.end=(2,0);doc.saveas(out/'native-reopen/source-export.dxf')
            settings=root/'settings.json';settings.write_text('{}');(out/'sheet.json').write_text('{}')
            for name in ('section.dwg','sheet.pdf'):(out/name).write_bytes(b'fictional test bytes')
            engine=root/'engine.exe';engine.write_bytes(b'fictional test runtime')
            proof=dict(artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()},inputs={str(p):digest(p) for p in (source,settings)},engine=str(engine),engine_sha256=digest(engine),dwg_sha256=digest(out/'section.dwg'),plot=dict(pdf_sha256=digest(out/'sheet.pdf')),settings={})
            def save():(out/'native-verification.json').write_text(json.dumps(proof))
            save()
            with self.assertRaisesRegex(ProjectError,'geometry/attributes mismatch'):native_stage(source,settings,{},out)
            original=proof['artifacts'].pop('sheet.pdf');save()
            with self.assertRaisesRegex(ValueError,'coverage missing'):native_stage(source,settings,{},out)
            proof['artifacts']['sheet.pdf']=original;proof['artifacts']['../source.dxf']=digest(source);save()
            with self.assertRaisesRegex(ValueError,'artifact changed'):native_stage(source,settings,{},out)
            del proof['artifacts']['../source.dxf'];proof['settings']={'changed':True};save()
            with self.assertRaisesRegex(ValueError,'settings differ'):native_stage(source,settings,{},out)
