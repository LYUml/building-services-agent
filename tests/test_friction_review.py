import copy
import unittest
from unittest.mock import patch
from bsa.friction_review import requests
from bsa.workflow_status import diagnose
from tests import test_stub_friction_contract as fixtures
from bsa.providers.stub_friction import common

class FrictionReviewTests(unittest.TestCase):
    def setUp(self):
        fixtures.FrictionContractTests.setUp(self)

    def test_review_preserves_source_basis_without_changing_numerical_result(self):
        payload=common(self.request,self.report,self.root);original=copy.deepcopy(payload)
        rows=requests(payload);self.assertEqual(len(rows),3)
        self.assertAlmostEqual(rows[0]['evidence']['length_over_diameter'],.75)
        self.assertEqual(rows[1]['evidence']['density_by_terminal']['T1']['classification'],'assumed')
        self.assertEqual(payload,original)
        payload['components']['T1']['cases']['minimum'].update(status='pending',regime='transition',reynolds=3000)
        pending=[r for r in requests(payload) if r['code']=='transitional_flow_method_required']
        self.assertEqual(len(pending),1);self.assertEqual(pending[0]['condition'],'minimum')
        self.assertEqual(requests({'schema':'other'}),[])

    def test_passing_execution_retains_separate_engineering_queue(self):
        plan=self.root/'plan.json';plan.write_text('{}');run=self.root/'run';run.mkdir();(run/'workflow.json').write_text('{}')
        source=dict(tasks=[dict(id='friction',kind='module_analysis')],requirements=[dict(id='R1',task='friction')])
        report=dict(tasks=dict(friction=dict(status='pass',scope='Numerical component only')),artifact_hashes={})
        module=dict(evidence='friction/result.json',evidence_sha256='0'*64,engineering_review_requests=[dict(code='whole_system_pressure_incomplete')])
        with patch('bsa.workflow_status.context',return_value=(source,report,dict(integrity_pass=True))),patch('bsa.workflow_status.module_state',return_value=module):
            result=diagnose(plan,run)
        self.assertTrue(result['execution_pass']);self.assertFalse(result['design_accepted']);self.assertEqual(result['actions'],[])
        self.assertEqual(result['engineering_actions'][0]['requirement_ids'],['R1'])
        self.assertEqual(result['engineering_actions'][0]['evidence'],'friction/result.json')

    def test_unavailable_module_cannot_create_engineering_requests(self):
        from bsa.workflow_status import module_state
        report=dict(artifact_hashes={'friction/result.json':'0'*64})
        result=dict(provider={'id':'fluids.native-stub-friction'},execution={'status':'unavailable'},acceptance={'status':'pending'},payload=None,payload_schema='bsa.straight-friction-components/1')
        with patch('bsa.modules.verify_result',return_value=result):
            state=module_state(self.root,report,dict(id='friction',kind='module_analysis'))
        self.assertEqual(state['engineering_review_requests'],[])

    def test_rejected_module_evidence_cannot_create_review_queue(self):
        from bsa.workflow_status import module_state
        with patch('bsa.modules.verify_result',side_effect=ValueError('changed native evidence')):
            with self.assertRaisesRegex(ValueError,'changed native evidence'):
                module_state(self.root,dict(artifact_hashes={'friction/result.json':'0'*64}),dict(id='friction',kind='module_analysis'))
