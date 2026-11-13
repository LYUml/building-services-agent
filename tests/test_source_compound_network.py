import copy
import unittest
from unittest.mock import patch
from bsa import source_compound_network as tool
from tests import test_source_tee_network as fixtures


class SourceCompoundNetworkTests(unittest.TestCase):
    def fixture(self):
        model=fixtures.SourceTeeNetworkTests().fixture()[0];d=model['devices'][0];d['properties'].update(AppliedTeeFromTrim_m=.12,AppliedCrossToTrim_m=.23)
        for name in ('A','D'):
            item=copy.deepcopy(d);item['id']=name;model['devices'].append(item)
        model['connections']=[{'from':'BEND-B.out','to':'A.in'}]
        fit=dict(absorbed_straight_sections=['A','D'],direct_inlet_source_port='BEND-B.out',external_interfaces=[dict(section='S',port='in',compound_port='lower',reach_m=.4,remaining_straight_m=2.6)],inherited_minimum_remainder_m=.05)
        return model,fit

    def test_explicit_absorption_retains_prior_trim_provenance(self):
        model,fit=self.fixture();original=copy.deepcopy(model)
        with patch.object(tool.bim,'validate'):actual,budgets=tool.compile_model(model,fit)
        self.assertEqual(model,original);self.assertEqual([d['id'] for d in actual['devices']],['S']);self.assertEqual(actual['connections'],[])
        props=actual['devices'][0]['properties'];self.assertEqual(props['AppliedTeeFromTrim_m'],.12);self.assertEqual(props['AppliedCrossToTrim_m'],.23);self.assertEqual(props['AppliedCompoundFromTrim_m'],.4)
        self.assertAlmostEqual(budgets[0]['remaining_m'],2.6)

    def test_unexpected_removed_link_or_changed_budget_rejects(self):
        model,fit=self.fixture();model['connections'].append({'from':'D.out','to':'S.in'})
        with self.assertRaisesRegex(ValueError,'Only'):tool.compile_model(model,fit)
        model,fit=self.fixture();fit['external_interfaces'][0]['remaining_straight_m']=2.5
        with self.assertRaisesRegex(ValueError,'budget'):tool.compile_model(model,fit)

    def test_connected_tree_and_disconnected_cycle(self):
        objects={name:{} for name in ('A','B','C')};ports={'a':dict(owner='A'),'b':dict(owner='B'),'c':dict(owner='C'),'b-out':dict(owner='B'),'a-in':dict(owner='A')};expected=dict(objects=objects,ports=ports,links=[('a','b'),('a','c')])
        with patch.object(tool.network,'inspect',return_value={}):self.assertTrue(tool.inspect('unused',expected)['one_connected_directed_product_tree'])
        expected['links']=[('a','b'),('b-out','a-in')]
        with patch.object(tool.network,'inspect',return_value={}):
            with self.assertRaisesRegex(ValueError,'disconnected'):tool.inspect('unused',expected)


if __name__=='__main__':unittest.main()
