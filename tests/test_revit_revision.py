"""Synthetic model-revision controls, independent of native host execution."""
import copy
import unittest
from bsa.engine import ProjectError
from bsa.revit_revision import audit_pipe


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
