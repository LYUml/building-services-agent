import copy
import unittest
from bsa.duct_coordination_diagnosis import calculate,pair_signature

class CoordinationDiagnosisTests(unittest.TestCase):
    def fixture(self):
        junction=dict(nodes=[dict(node='J',connection_requirement='unequal_section_tee_required',incidents=[dict(section=n) for n in ['A','B','C']])])
        fit=dict(remaining_source_connection_nodes=[dict(node='J',requirement='unequal_section_tee_required')])
        a=dict(pair=['gA','gB'],names=['A','B'],type='pierce');b=dict(a,type='manifold_mesh_overlap',overlap_volume_m3=.001)
        report=dict(intersections=[a,b],clearance_violations=[dict(pair=['gA','gD'],names=['A','BEND-X'],type='touch')],checks=dict(no_intersections=False,clearance=False),calculated_checks_pass=False)
        return junction,fit,report,dict(gA='A',gB='B',gC='C',gD='BEND-X'),{tuple(sorted(['gA','gD']))}

    def test_two_engine_records_are_one_pair_without_waiving_failure(self):
        args=self.fixture();original=copy.deepcopy(args);r=calculate(*args)
        self.assertEqual(r['raw_intersection_records'],2);self.assertEqual(r['unique_intersection_pairs'],1)
        self.assertEqual(r['intersection_associations'],{'unresolved_source_connection':1})
        self.assertEqual(r['clearance_associations'],{'linked_interface_clearance':1})
        self.assertEqual(r['status'],'coordination_failed');self.assertFalse(r['design_accepted'])
        self.assertFalse(r['intersections'][0]['waived']);self.assertFalse(r['engineering_actions'][0]['node_specific_authoring_executed']);self.assertEqual(args,original)

    def test_nonadjacent_and_linked_overlap_do_not_get_hidden_as_unbuilt_tee(self):
        args=list(self.fixture());args[2]['intersections']=[dict(pair=['gB','gD'],names=['B','BEND-X'],type='pierce')]
        r=calculate(*args);self.assertEqual(r['intersection_associations'],{'nonadjacent_interference':1})
        args[4].add(tuple(sorted(['gB','gD'])));r=calculate(*args);self.assertEqual(r['intersection_associations'],{'linked_interface_intersection':1})

    def test_mismatched_native_identity_and_source_connection_reject(self):
        for change in ['name','guid','connection']:
            args=list(self.fixture())
            if change=='name':args[2]['intersections'][0]['names']=['A','other']
            if change=='guid':args[2]['intersections'][0]['pair']=['gA','missing']
            if change=='connection':args[1]['remaining_source_connection_nodes'][0]['requirement']='other'
            with self.assertRaises(ValueError):calculate(*args)

    def test_pair_signature_retains_overlap_and_ignores_record_order(self):
        _,_,report,_,_=self.fixture();report.update(physical_element_count=4,represented_element_count=4,loaded_geometry_count=4,valid_geometry_count=4)
        report['intersections'][1]['engine_distance_m']=None
        other=copy.deepcopy(report);other['intersections'].reverse();self.assertEqual(pair_signature(report),pair_signature(other))
        other['intersections'][0]['overlap_volume_m3']=.002;self.assertNotEqual(pair_signature(report),pair_signature(other))

if __name__=='__main__':unittest.main()
