import unittest
from bsa.cable_bend_regulations import classification_source
from bsa.cable_bend_limits import evaluate


class CableEvidenceSlotTests(unittest.TestCase):
    def test_legacy_shared_document(self):
        self.assertEqual(classification_source({'SourceSHA256':'shared'}),('SourceSHA256','shared'))

    def test_explicit_classification_is_independent(self):
        self.assertEqual(classification_source({'SourceSHA256':'product','ClassificationSourceSHA256':'construction'}),('ClassificationSourceSHA256','construction'))

    def test_empty_explicit_slot_never_uses_product_document(self):
        for value in ('',None):
            self.assertEqual(classification_source({'SourceSHA256':'product','ClassificationSourceSHA256':value}),('ClassificationSourceSHA256',value))

    def test_product_limit_uses_its_own_document(self):
        observed=dict(bend_radius_m=.3,envelope_radius_m=.01)
        row=dict(product_reference='test',diameter_m=.02,diameter_basis='nominal',condition='installed',radius_reference='inside',minimum_radius_m=.28)
        source=dict(sha256='product',kind='assumption')
        meta=dict(ProductReference='test',SourceSHA256='product',ClassificationSourceSHA256='construction',InstallationCondition='installed')
        self.assertEqual(evaluate(observed,row,meta,source)['status'],'pass')
        meta['SourceSHA256']='construction'
        self.assertEqual(evaluate(observed,row,meta,source)['status'],'fail')
