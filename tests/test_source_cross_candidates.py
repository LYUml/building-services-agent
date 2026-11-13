import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa import source_cross_candidates as tool
from bsa import rectangular_cross_transitions as composition


class SourceCrossCandidatesTests(unittest.TestCase):
    def fixture(self):
        node=dict(node='J',degree=4,point_m=[4.,5.,0.],connection_requirement='multi_branch_connection_required',incidents=[dict(section=s,role=role,outward_unit_vector=ray,width_m=w,height_m=h) for s,role,ray,w,h in [('A','incoming',[0.,1.,0.],.6,.3),('B','outgoing',[0.,-1.,0.],.4,.3),('C','outgoing',[-1.,0.,0.],.3,.2),('D','outgoing',[1.,0.,0.],.3,.2)]])
        basis=dict(project_uuid='92244432-6bcd-42a7-a995-51ec0a29754b',wall_thickness_m=dict(value=.001),elevation_m=dict(value=3))
        row=dict(core_section_m=[.6,.3],main_half_length_m=.5,branch_length_m=.5,start_length_m=.05,end_length_m=.05,upstream_angle_degrees=30,transition_method='explicit_station_brep',classification='assumed',source='Synthetic explicit cross construction')
        return node,basis,row

    def test_original_incidents_and_source_rays_preserved(self):
        args=self.fixture();original=copy.deepcopy(args);data,binding=tool.compile_node(*args)
        self.assertEqual(args,original);self.assertEqual(binding,{'main-a':'A','main-b':'B','branch-a':'C','branch-b':'D'})
        self.assertEqual(data['cross']['port_directions']['main-a'],'SINK');self.assertEqual(data['arms']['main-a'],{'kind':'bare'})
        child=composition.children(data['cross'],data['arms'])['main-b'];self.assertAlmostEqual(child['transition_length_m'],.2/(2*math.tan(math.radians(15))))

    def test_not_four_perpendicular_arms_rejects(self):
        node,basis,row=self.fixture();node['incidents'][2]['outward_unit_vector']=[0,1,0]
        with self.assertRaisesRegex(ValueError,'pairs'):tool.compile_node(node,basis,row)
        node,basis,row=self.fixture();node['incidents'].pop()
        with self.assertRaises(ValueError):tool.compile_node(node,basis,row)

    def test_saved_four_arm_transition_material_and_ports(self):
        data,_=tool.compile_node(*self.fixture())
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'runs') as folder:
            folder=Path(folder);source=folder/'project.json';source.write_text(json.dumps(data));result=composition.run(source,folder/'native')
            self.assertEqual(result['checks']['components'],4);self.assertEqual(result['checks']['ports'],10);self.assertEqual(result['checks']['actual_links'],3);self.assertEqual(result['checks']['euler_characteristic'],-4)
            changed=copy.deepcopy(data['arms']);changed['branch-a']['end_section_m'][0]+=.01
            with self.assertRaises(ValueError):composition.inspect(folder/'native/assembly.ifc',data['cross'],changed)

    def test_inherited_remaining_budget_blocks_cross_and_coverage_is_exact(self):
        node,basis,row=self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);source=folder/'network';source.mkdir();tees=folder/'tees';tees.mkdir();selection=folder/'selection';selection.mkdir();basis_path=folder/'basis.json';basis_path.write_text(json.dumps(basis))
            (selection/'selection.json').write_text(json.dumps(dict(source=dict(basis=str(basis_path)))))
            (selection/'junction.json').write_text(json.dumps(dict(nodes=[node])))
            (tees/'tee-candidates.json').write_text(json.dumps(dict(source=dict(selection=str(selection)))))
            parent=dict(source=str(tees),budgets=[dict(section=s,remaining_m=.4 if s=='A' else 3.,minimum_remainder_m=.05) for s in ('A','B','C','D')])
            (source/'network.json').write_text(json.dumps(parent));policy=dict(source='Synthetic inherited two-end study',nodes={'J':row})
            _,rows,budgets,blocked=tool.prepare(source,policy,folder/'prepared')
            self.assertIn('J',blocked);self.assertIn('A',blocked['J'][0]);self.assertEqual(set(rows),{'J'})
            self.assertLess(budgets[0]['remaining_m'],0)
            policy['nodes']={}
            with self.assertRaisesRegex(ValueError,'covered'):tool.prepare(source,policy,folder/'missing')
            self.assertFalse((folder/'missing').exists())


if __name__=='__main__':unittest.main()
