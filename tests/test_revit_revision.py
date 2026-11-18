"""Synthetic model-revision controls, independent of native host execution."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from bsa.engine import ProjectError
from bsa.revit_revision import audit_pipe
from bsa.source_refs import file_hash
from scripts.verify_revit_automation_reopen import verify


class RevitRevisionTests(unittest.TestCase):
    def setUp(self):
        self.pipe = dict(unique_id='pipe-a', type_unique_id='type-a', system_type_unique_id='system-a',
                         level_unique_id='level-a', curve_kind='Line', endpoints_m=[[0,0,0],[2,0,0]],
                         diameter_m=0.05, length_m=2,
                         creation_provenance=dict(schema_version=1, original_element_unique_id='pipe-a',
                             element_identity_matches=True, creation_request=dict(Source='synthetic test basis',
                                 StartMetres=[0,0,0], EndMetres=[2,0,0], DiameterMetres=0.05,
                                 PipeTypeUniqueId='type-a', SystemTypeUniqueId='system-a', LevelUniqueId='level-a')))

    def test_unchanged_and_reversed_segment(self):
        for reverse in (False, True):
            pipe=copy.deepcopy(self.pipe)
            if reverse: pipe['endpoints_m'].reverse()
            result=audit_pipe(pipe, 1e-5)
            self.assertEqual(result['status'], 'consistent')
            self.assertFalse(result['source_verified'])
            self.assertFalse(result['design_accepted'])

    def test_automation_reopen_reconciles_saved_pipe_and_rejects_displacement(self):
        runs = Path(__file__).resolve().parents[1] / 'runs'
        with TemporaryDirectory(dir=runs) as temporary:
            root = Path(temporary)

            def save(name, data):
                path = root / name
                path.write_text(json.dumps(data), encoding='utf-8')
                return path

            source_hash, adapter_hash, reopen_hash = 'a'*64, 'b'*64, 'c'*64
            authored = root / 'authored.rvt'
            authored.write_bytes(b'synthetic saved file')
            authored_hash = file_hash(authored)
            stored = self.pipe['creation_provenance']['creation_request']
            stored.update(DocumentPath='X:/creation/input.rvt', SavedRvtSha256=source_hash)
            request = save('pipe-request.json', dict(stored, DocumentPath='X:/local/test.rvt'))
            request_hash = file_hash(request)
            save('preparation.json', dict(operation='create-pipe', saved_rvt_sha256=source_hash,
                 request_sha256=request_hash, assembly_sha256=adapter_hash))
            created = save('creation.json', dict(input_rvt_sha256=source_hash, request_sha256=request_hash,
                adapter_sha256=adapter_hash, saved_rvt_sha256=authored_hash,
                transaction_result={'unique_id': self.pipe['unique_id'], 'connector_count': 2}))
            reopen = save('reopen.json', dict(saved_rvt_sha256=authored_hash, request_sha256=reopen_hash,
                                            assembly_sha256=adapter_hash))
            self.pipe['connectors'] = [dict(id=index, origin_m=point, domain='DomainPiping',
                                            connector_type='End', physically_connected=False, references=[])
                                       for index, point in enumerate(self.pipe['endpoints_m'], start=1)]
            inventory = dict(document_path='X:/reopen/input.rvt', saved_rvt_sha256=authored_hash,
                             request_sha256=reopen_hash, adapter_sha256=adapter_hash, units='metres',
                             pipes=[self.pipe], fittings=[])
            observed = save('inventory.json', inventory)
            result = verify(root, created, authored, observed, reopen, 0.001)
            self.assertTrue(result['pipe_matches_capture'])
            self.assertFalse(result['native_execution_authenticated'])
            self.assertEqual(result['connector_endpoint_error_m'], 0)
            self.pipe['connectors'][1]['origin_m'] = self.pipe['connectors'][0]['origin_m']
            save('inventory.json', inventory)
            with self.assertRaisesRegex(ValueError, 'distinct curve endpoints'):
                verify(root, created, authored, observed, reopen, 0.001)
            self.pipe['connectors'][1]['origin_m'] = self.pipe['endpoints_m'][1]
            self.pipe['endpoints_m'] = [[0, 1, 0], [2, 1, 0]]
            save('inventory.json', inventory)
            with self.assertRaisesRegex(ValueError, 'identity or geometry'):
                verify(root, created, authored, observed, reopen, 0.001)

    def test_translation_with_same_length_and_diameter_is_detected(self):
        self.pipe['endpoints_m']=[[0,1,0],[2,1,0]]
        result=audit_pipe(self.pipe, 1e-5)
        self.assertEqual(result['reasons'], ['endpoints_changed'])

    def test_copy_does_not_inherit_identity_acceptance(self):
        self.pipe['unique_id']='copy-b'
        self.assertIn('original_identity_mismatch', audit_pipe(self.pipe, 1e-5)['reasons'])

    def test_type_system_level_diameter_and_curve_changes(self):
        for key, value, reason in (
            ('type_unique_id','new','type_unique_id_changed_or_missing'),
            ('system_type_unique_id','new','system_type_unique_id_changed_or_missing'),
            ('level_unique_id','new','level_unique_id_changed_or_missing'),
            ('diameter_m',0.08,'diameter_changed'),
            ('curve_kind','Arc','curve_is_not_original_straight_segment')):
            pipe=copy.deepcopy(self.pipe);pipe[key]=value
            with self.subTest(key=key): self.assertIn(reason,audit_pipe(pipe,1e-5)['reasons'])

    def test_missing_provenance_is_pending_invalid_coordinates_rejected(self):
        self.assertEqual(audit_pipe({},1e-5)['status'],'pending')
        self.pipe['endpoints_m'][0][0]=float('nan')
        with self.assertRaises(ProjectError): audit_pipe(self.pipe,1e-5)


if __name__=='__main__': unittest.main()
