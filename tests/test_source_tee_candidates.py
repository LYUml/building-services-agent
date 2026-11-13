import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bsa import source_tee_candidates as tool
from bsa import rectangular_tee_transitions as composition

class SourceTeeCandidatesTests(unittest.TestCase):
    def fixture(self):
        incidents=[dict(section=s,role=role,line_handle=s,outward_unit_vector=ray,source_centreline_length_m=3,width_m=w,height_m=h,flow_L_s=q) for s,role,ray,w,h,q in [('A','incoming',[-1,0,0],.6,.3,500),('B','outgoing',[1,0,0],.4,.3,300),('C','outgoing',[0,1,0],.3,.2,200)]]
        junction=dict(source_correspondence_pass=True,nodes=[dict(node='J',degree=3,point_m=[4,5,0],connection_requirement='unequal_section_tee_required',incidents=incidents)])
        basis=dict(project_uuid='e307360f-2365-4f9a-8f78-d96dfba5fddb',wall_thickness_m=dict(value=.001,classification='assumed',source='Synthetic gauge'),elevation_m=dict(value=3,classification='assumed',source='Synthetic study elevation'),profile_interpretation=dict(value='scheduled_nominal_as_clear_internal',classification='assumed',source='Synthetic convention'))
        row=dict(core_section_m=[.6,.3],main_half_length_m=.5,branch_length_m=.5,start_length_m=.05,end_length_m=.05,upstream_angle_degrees=45,transition_method='upstream_mep_shape',classification='assumed',source='Synthetic ideal geometry, not products')
        return junction,basis,dict(basis='Synthetic source tee study',nodes={'J':row})

    def test_source_rays_sections_flow_directions_and_identity_preserved(self):
        j,b,p=self.fixture();original=copy.deepcopy((j,b,p))
        with tempfile.TemporaryDirectory() as folder:
            rows=tool.prepare(j,b,p,Path(folder)/'inputs');r=rows['J']
            self.assertTrue(r['fit']['plan_extent_check_pass']);self.assertFalse(r['fit']['installation_elevation_verified'])
            self.assertEqual(r['binding']['arms'],{'main-a':'A','main-b':'B','branch':'C'})
            self.assertEqual(r['spec']['port_directions'],{'main-a':'SINK','main-b':'SOURCE','branch':'SOURCE'})
            self.assertEqual(r['data']['arms']['main-a'],{'kind':'bare'})
            self.assertEqual(r['data']['arms']['branch']['end_section_m'],[.3,.2]);self.assertEqual((j,b,p),original)

    def test_both_end_budget_blocks_candidate_that_passes_local_extent(self):
        j,b,p=self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            rows=tool.prepare(j,b,p,Path(folder)/'inputs')
            selected=dict(policy=dict(minimum_remainder_m=dict(value=.05)),fit=dict(source_section_budgets=[dict(section=s,source_centreline_m=3,declared_elbow_trims_m={'opposite-end':3-r},remaining_after_declared_elbows_m=r,other_fitting_trims_known=False) for s,r in [('A',1),('B',.7),('C',3)]]))
            budgets,blocked=tool.budgets(selected,rows);self.assertIn('J',blocked);self.assertTrue(rows['J']['fit']['plan_extent_check_pass'])
            self.assertLess(next(r for r in budgets if r['section']=='B')['remaining_after_known_fittings_m'],0)

    def test_all_source_nodes_and_explicit_geometry_are_required(self):
        j,b,p=self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            wrong=copy.deepcopy(p);wrong['nodes']={}
            with self.assertRaises(ValueError):tool.prepare(j,b,wrong,Path(folder)/'missing')
            self.assertFalse((Path(folder)/'missing').exists())
        bad=copy.deepcopy(p['nodes']['J']);bad.pop('upstream_angle_degrees')
        with self.assertRaises(ValueError):tool.compile_node(j,b,'J',bad)
        j['nodes'][0]['incidents'][1]['outward_unit_vector']=[.5,.5,0]
        with self.assertRaises(ValueError):tool.compile_node(j,b,'J',p['nodes']['J'])

    def test_upstream_single_dimension_station_mismatch_is_explicitly_blocked(self):
        j,b,p=self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            rows=tool.prepare(j,b,p,Path(folder)/'inputs')
            self.assertFalse(rows['J']['transition_screening']['main-b']['supported'])
            selected=dict(policy=dict(minimum_remainder_m=dict(value=.05)),fit=dict(source_section_budgets=[]))
            _,blocked=tool.budgets(selected,rows);self.assertIn('Upstream transition',blocked['J'][0])

    def test_actual_native_composition_in_selected_external_workspace(self):
        import ifcopenshell
        j,b,p=self.fixture();p['nodes']['J']['transition_method']='explicit_station_brep'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(root)}):
                rows=tool.prepare(j,b,p,root/'inputs');r=rows['J'];project=root/'inputs'/r['directory']/'project.json'
                native=composition.run(project,root/'native');self.assertTrue(native['assembly_checks_pass'])
                f=ifcopenshell.open(str(root/'native/assembly.ifc'));self.assertEqual(len(f.by_type('IfcDuctFitting')),3);self.assertEqual(len(f.by_type('IfcDistributionPort')),7)
                with self.assertRaises(ValueError):composition.run(project,root.parent/'outside-source-tee-native')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaises(ValueError):composition.run(project,root/'unselected')
                self.assertFalse((root/'unselected').exists())

if __name__=='__main__':unittest.main()
