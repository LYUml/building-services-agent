import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa import network_analysis_access as tool


class RecordedFittingAccessTests(unittest.TestCase):
    def fixture(self,root):
        # Fictional saved-byte controls, not engineering or publisher data.
        rows=[dict(product_guid='same-body',inlet_port_guid='in',outlet_port_guid=str(i),
            predefined_type='JUNCTION',status='source_data_required' if i%2 else 'table_support_missing',
            affected_outlet_port_guids=[str(i)],required_evidence=['Fictional missing input']) for i in range(25)]
        path=root/'fitting-data.json';path.write_text(json.dumps(dict(data_requests=rows)))
        return path,tool.digest(path)

    def test_stable_pages_filters_and_exact_directed_path(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            root=Path(folder);path,sha=self.fixture(root);original=path.read_bytes()
            first=tool.list_requests(root,sha);second=tool.list_requests(root,sha,offset=first['next_offset'])
            self.assertEqual([r['outlet_port_guid'] for r in first['requests']+second['requests']],[str(i) for i in range(25)])
            self.assertIsNone(second['next_offset'])
            filtered=tool.list_requests(root,sha,status='source_data_required');self.assertEqual(filtered['total'],12)
            selected=tool.read_request(root,sha,'same-body','in','17');self.assertEqual(selected['request']['outlet_port_guid'],'17')
            self.assertFalse(selected['design_accepted']);self.assertIn('Recorded bytes only',selected['verification'])
            with self.assertRaises(ValueError):tool.read_request(root,sha,'same-body','17','in')
            self.assertEqual(path.read_bytes(),original)
            path.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError,'differs'):tool.list_requests(root,sha)

    def test_invalid_limits_hash_workspace_and_oversized_records(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BSA_PROJECT_ROOT':folder}):
            root=Path(folder);path,sha=self.fixture(root)
            for kwargs in (dict(offset=-1),dict(offset=True),dict(limit=21),dict(limit=0),dict(status='accepted')):
                with self.assertRaises(ValueError):tool.list_requests(root,sha,**kwargs)
            with self.assertRaises(ValueError):tool.list_requests(root,'bad')
            with tempfile.TemporaryDirectory() as other:
                with self.assertRaisesRegex(ValueError,'host selected'):tool.list_requests(other,sha)
            path.write_bytes(b' '*(tool.LIMIT+1))
            with self.assertRaisesRegex(ValueError,'bounded'):tool.list_requests(root,hashlib.sha256(path.read_bytes()).hexdigest())
