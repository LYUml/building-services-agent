"""Synthetic model-revision controls, independent of native host execution."""
import copy
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
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

            source_hash, adapter_hash = 'a'*64, 'b'*64
            authored = root / 'authored.rvt'
            authored.write_bytes(b'synthetic saved file')
            authored_hash = file_hash(authored)
            stored = self.pipe['creation_provenance']['creation_request']
            stored.update(DocumentPath='X:/creation/input.rvt', SavedRvtSha256=source_hash)
            request = save('pipe-request.json', dict(stored, DocumentPath='X:/local/test.rvt'))
            request_hash = file_hash(request)
            write_preparation = dict(operation='create-pipe', saved_rvt_sha256=source_hash,
                                     request_sha256=request_hash, assembly_sha256=adapter_hash)
            save('preparation.json', write_preparation)
            self.pipe['id'] = '1042'
            receipt = dict(input_rvt_sha256=source_hash, request_sha256=request_hash,
                adapter_sha256=adapter_hash, saved_rvt_sha256=authored_hash,
                saved_reopen_verified=False, design_accepted=False,
                transaction_result=dict(unique_id=self.pipe['unique_id'], element_id=self.pipe['id'], connector_count=2,
                                        connectors=[dict(id=1, origin_m=[0, 0, 0]), dict(id=2, origin_m=[2, 0, 0])],
                                        saved=False, connected_system_verified=False, design_accepted=False,
                                        source=stored['Source'], diameter_m=0.05, length_m=2))
            created = save('creation.json', receipt)
            reopen_request = save('inventory-request.json', dict(SavedRvtSha256=authored_hash))
            reopen_hash = file_hash(reopen_request)
            reopen = save('reopen.json', dict(operation='inventory', saved_rvt_sha256=authored_hash,
                                            request_sha256=reopen_hash, assembly_sha256=adapter_hash))
            self.pipe['connectors'] = [dict(id=index, origin_m=point, domain='DomainPiping',
                                            connector_type='End', physically_connected=False, references=[])
                                       for index, point in enumerate(self.pipe['endpoints_m'], start=1)]
            inventory = dict(document_path='X:/reopen/input.rvt', saved_rvt_sha256=authored_hash,
                             request_sha256=reopen_hash, adapter_sha256=adapter_hash, units='metres',
                             pipes=[self.pipe], fittings=[])
            observed = save('inventory.json', inventory)
            result = verify(root, created, authored, observed, reopen, 0.001)
            self.assertTrue(result['pipe_matches_capture'])
            self.assertEqual(result['pipe_element_id'], '1042')
            duplicate = dict(id='1042', unique_id='duplicate-fitting',
                             connector_manager_available=False, connectors=None)
            save('inventory.json', dict(inventory, fittings=[duplicate]))
            with self.assertRaisesRegex(ValueError, 'element_id 1042 is shared'):
                verify(root, created, authored, observed, reopen, 0.001)
            save('inventory.json', inventory)
            self.assertFalse(result['native_execution_authenticated'])
            self.assertEqual(result['connector_endpoint_error_m'], 0)
            self.assertTrue(result['creation_connector_matches'])
            self.assertEqual([row['deviation_m'] for row in result['creation_connector_readback']], [0, 0])
            older = copy.deepcopy(receipt)
            del older['transaction_result']['connectors']
            save('creation.json', older)
            older_result = verify(root, created, authored, observed, reopen, 0.001)
            self.assertFalse(older_result['creation_connector_matches'])
            self.assertEqual(older_result['creation_connector_readback'], [])
            moved_connector = copy.deepcopy(receipt)
            moved_connector['transaction_result']['connectors'][0]['origin_m'] = [0, 0.02, 0]
            save('creation.json', moved_connector)
            with self.assertRaisesRegex(ValueError, r'Reopened connector 1 differs from the creation readback \(deviation 0\.02 m\)'):
                verify(root, created, authored, observed, reopen, 0.001)
            save('creation.json', receipt)
            self.assertEqual(result['connector_endpoint_matches'], [
                dict(connector_id=1, origin_m=[0, 0, 0], endpoint_m=[0, 0, 0], error_m=0),
                dict(connector_id=2, origin_m=[2, 0, 0], endpoint_m=[2, 0, 0], error_m=0),
            ])
            self.assertEqual(result['reopen_request_sha256'], reopen_hash)
            self.assertEqual(result['write_request_sha256'], request_hash)
            self.assertEqual(result['write_preparation_sha256'], file_hash(root/'preparation.json'))
            self.assertEqual(result['reopen_preparation_sha256'], file_hash(reopen))
            self.assertEqual(result['tolerance_m'], 0.001)
            with self.assertRaisesRegex(ValueError, 'connector-to-endpoint pairing is ambiguous'):
                verify(root, created, authored, observed, reopen, 2.0)
            self.pipe['connectors'].reverse()
            save('inventory.json', inventory)
            reversed_result = verify(root, created, authored, observed, reopen, 0.001)
            self.assertEqual(reversed_result['connector_endpoint_matches'], result['connector_endpoint_matches'])
            self.pipe['connectors'].reverse()
            save('inventory.json', inventory)
            for field in ('saved_reopen_verified', 'design_accepted'):
                with self.subTest(unsupported_claim=field):
                    save('creation.json', {**receipt, field: True})
                    with self.assertRaisesRegex(ValueError, 'must leave saved reopening and design acceptance unverified'):
                        verify(root, created, authored, observed, reopen, 0.001)
            save('creation.json', receipt)
            for field in ('saved', 'connected_system_verified', 'design_accepted'):
                with self.subTest(unsupported_transaction_claim=field):
                    altered = dict(receipt, transaction_result={**receipt['transaction_result'], field: True})
                    save('creation.json', altered)
                    with self.assertRaisesRegex(ValueError, 'Pipe transaction readback must leave'):
                        verify(root, created, authored, observed, reopen, 0.001)
            save('creation.json', receipt)
            original_request = request.read_bytes()
            same_model = dict(json.loads(original_request), SavedRvtSha256=authored_hash)
            save('pipe-request.json', same_model)
            revised_hash = file_hash(request)
            save('preparation.json', dict(write_preparation, saved_rvt_sha256=authored_hash,
                                          request_sha256=revised_hash))
            save('creation.json', dict(receipt, input_rvt_sha256=authored_hash, request_sha256=revised_hash))
            with self.assertRaisesRegex(ValueError, 'Authored RVT must differ'):
                verify(root, created, authored, observed, reopen, 0.001)
            request.write_bytes(original_request)
            save('preparation.json', write_preparation)
            save('creation.json', receipt)
            arguments = dict(write_stage=root.name, creation=f'{root.name}/{created.name}',
                             authored=f'{root.name}/{authored.name}', inventory=f'{root.name}/{observed.name}',
                             reopen_preparation=f'{root.name}/{reopen.name}', tolerance_m=0.001)
            env = {**os.environ, 'BSA_PROJECT_ROOT': str(runs)}
            command = [sys.executable, '-m', 'bsa.cli', 'revit-verify-automation-reopen']
            for key, value in arguments.items():
                command.extend(('--' + key.replace('_', '-'), str(value)))
            completed = subprocess.run(command, cwd=runs, env=env, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(completed.stdout), result)

            if importlib.util.find_spec('mcp'):
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client

                async def check_stdio():
                    params = StdioServerParameters(command=sys.executable, args=['-m', 'bsa.mcp_server'],
                                                   cwd=str(runs), env=env)
                    async with stdio_client(params) as streams:
                        async with ClientSession(*streams) as session:
                            await session.initialize()
                            response = await session.call_tool('bsa_verify_revit_automation_reopen', arguments)
                            self.assertFalse(response.isError, response.content)
                            self.assertEqual(response.structuredContent, result)
                            mismatch = await session.call_tool('bsa_verify_revit_automation_reopen',
                                                               {**arguments, 'authored': arguments['creation']})
                            self.assertTrue(mismatch.isError)
                            self.assertIn('does not match', mismatch.content[0].text)

                asyncio.run(check_stdio())
            original_request = reopen_request.read_bytes()
            reopen_request.write_bytes(original_request + b'\n')
            with self.assertRaisesRegex(ValueError, 'staged inventory request'):
                verify(root, created, authored, observed, reopen, 0.001)
            save('inventory-request.json', dict(SavedRvtSha256=authored_hash, UnexpectedField=True))
            modified_hash = file_hash(reopen_request)
            save('reopen.json', dict(operation='inventory', saved_rvt_sha256=authored_hash,
                                    request_sha256=modified_hash, assembly_sha256=adapter_hash))
            save('inventory.json', dict(inventory, request_sha256=modified_hash))
            with self.assertRaisesRegex(ValueError, 'staged inventory request'):
                verify(root, created, authored, observed, reopen, 0.001)
            reopen_request.write_bytes(original_request)
            save('reopen.json', dict(operation='inventory', saved_rvt_sha256=authored_hash,
                                    request_sha256=reopen_hash, assembly_sha256=adapter_hash))
            save('inventory.json', inventory)
            for field, value in [('diameter_m', 0.07), ('length_m', True), ('source', 'different basis'),
                                 ('element_id', '1043'), ('element_id', 1042)]:
                with self.subTest(field=field):
                    altered = dict(receipt, transaction_result={**receipt['transaction_result'], field: value})
                    save('creation.json', altered)
                    with self.assertRaisesRegex(ValueError, field):
                        verify(root, created, authored, observed, reopen, 0.001)
            save('creation.json', receipt)
            self.pipe['connectors'][0]['physically_connected'] = True
            save('inventory.json', inventory)
            with self.assertRaisesRegex(ValueError, 'physical_flag_without_physical_reference'):
                verify(root, created, authored, observed, reopen, 0.001)
            self.pipe['connectors'][0]['references'] = [
                dict(owner_unique_id='unlisted-equipment', connector_id=1, connector_type='End'),
            ]
            save('inventory.json', inventory)
            with self.assertRaisesRegex(ValueError, 'unresolved connector evidence: target_outside_inventory'):
                verify(root, created, authored, observed, reopen, 0.001)
            self.pipe['connectors'][0]['references'] = []
            self.pipe['connectors'][0]['physically_connected'] = False
            self.pipe['connectors'][1]['origin_m'] = self.pipe['connectors'][0]['origin_m']
            save('inventory.json', inventory)
            with self.assertRaisesRegex(ValueError, 'distinct curve endpoints'):
                verify(root, created, authored, observed, reopen, 0.001)
            failed = subprocess.run(command, cwd=runs, env=env, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertIn('distinct curve endpoints', failed.stderr)
            self.assertIn('connector 2, deviation 2 m', failed.stderr)
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
