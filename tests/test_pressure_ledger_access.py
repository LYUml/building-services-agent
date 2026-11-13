import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bsa import pressure_ledger_access as access
from bsa.source_pressure_ledger import calculate
from bsa.cli import digest
from tests import test_source_pressure_ledger as fixtures


class LedgerAccessTests(unittest.TestCase):
    def fixture(self,root):
        out=Path(root).resolve()/'ledger';out.mkdir();data=calculate(*fixtures.PressureLedgerTests().fixture())
        (out/'pressure-ledger.json').write_text(json.dumps(data));sha=digest(out/'pressure-ledger.json')
        (out/'ledger.json').write_text(json.dumps(dict(ledger_sha256=sha)));return out,data,sha

    def test_bounded_identity_reads_keep_signed_null_and_missing_scope(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            out,data,sha=self.fixture(folder);r=access.summary(out,data);self.assertEqual(r['record_sha256'],sha)
            self.assertEqual(access.list_gaps(out,sha,limit=1)['total'],1)
            row=access.read_outlet(out,sha,'b')['outlet'];self.assertIsNone(row['complete_total_pressure_drop_Pa']);self.assertEqual(row['conditional_signed_table_subtotal_Pa'],-2.)
            self.assertTrue(row['unresolved_scope'])
            for value in (True,0,21,'2'):
                with self.assertRaises(ValueError):access.list_gaps(out,sha,limit=value)
            with self.assertRaises(ValueError):access.read_outlet(out,sha,'absent')
            with patch.object(access,'LIMIT',1):
                with self.assertRaisesRegex(ValueError,'bounded'):access.recorded(out,sha)
            (out/'pressure-ledger.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'inspected identity'):access.list_gaps(out,sha)

    def test_manifest_mutation_during_inspection_rejects(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            out,data,sha=self.fixture(folder)
            def changed(_):
                p=out/'ledger.json';p.write_text(json.dumps(dict(ledger_sha256=sha,changed=True)));return data
            with patch.object(access.ledger,'verify',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during inspection'):access.inspect(out)
