import copy
import json
from pathlib import Path
import tempfile
import unittest
import ezdxf
from bsa.duct_equivalent import calculate as friction
from bsa.duct_junction_review import inspect
from bsa.duct_elbow_backbone import compile_model,inspect_saved
from bsa.duct_backbone_ifc import export_storey
from bsa import elbow_radius_selection as selection
from tests import test_duct_backbone_ifc as backbone_fixtures

ROOT=Path(__file__).resolve().parents[1]

class RadiusSelectionTests(unittest.TestCase):
    def setUp(self):
        fixture=backbone_fixtures.DuctBackboneIFCTests();fixture.setUp();self.basis=fixture.basis;self.air=fixture.schedule['air']
        doc=ezdxf.new();doc.units=6;points=dict(R=[-3,0,0],A=[0,0,0],B=[0,1,0],Z=[3,1,0]);entries={};edges=[];rows=[]
        for sid,a,b in [('S0','R','A'),('S1','A','B'),('S2','B','Z')]:
            line=doc.modelspace().add_line(points[a],points[b]);entries[sid]=dict(line_handle=line.dxf.handle,from_node=a,to_node=b,from_m=points[a],to_m=points[b]);edges.append(dict(id=sid,**{'from':a,'to':b}))
            inputs=dict(width_m=.6,height_m=.3,flow_m3_s=.5);rows.append(dict(id=sid,inputs=inputs,calculation=friction(**inputs,**self.air),failures=[]))
        self.s=dict(status='pass',air=self.air,sections=rows,flow_aggregation=dict(root='R',sections=edges,section_flow_L_s={e['id']:500 for e in edges},leaf_flow_L_s={'Z':500},total_flow_L_s=500,topology_pass=True,flow_conserved=True,basis='Synthetic zigzag'))
        self.j=inspect(doc,self.s,dict(basis='Synthetic binding',sections=entries))
        self.policy=dict(basis='Explicit synthetic geometric choices; not products',minimum_remainder_m=dict(value=.1,classification='design_target',source='Synthetic study reserve'),nodes={n:[dict(id=i,radius_m=r,penalty=c,classification='design_target',source='Synthetic supplied geometric radius') for i,r,c in [('preferred',.9,0),('compact',.4,1)]] for n in ('A','B')})

    def test_two_end_constraints_choose_feasible_combination_and_preserve_inputs(self):
        original=copy.deepcopy((self.j,self.s,self.basis,self.policy));result=selection.calculate(self.j,self.s,self.basis,self.policy)
        self.assertEqual(result['status'],'candidate_selected');self.assertEqual(result['objective'],2)
        self.assertEqual({r['id'] for r in result['selected'].values()},{'compact'})
        self.assertEqual((self.j,self.s,self.basis,self.policy),original)
        self.assertFalse(result['fit']['full_fitting_trim_complete']);self.assertFalse(result['design_accepted'])
        self.assertAlmostEqual(next(r for r in result['fit']['source_section_budgets'] if r['section']=='S1')['remaining_after_declared_elbows_m'],.2)

    def test_infeasible_policy_and_invalid_radius_retain_no_selection(self):
        for n in self.policy['nodes']:self.policy['nodes'][n]=self.policy['nodes'][n][:1]
        result=selection.calculate(self.j,self.s,self.basis,self.policy);self.assertEqual(result['status'],'no_feasible_candidate');self.assertIsNone(result['selected_radii'])
        self.policy['nodes']['A'][0]['radius_m']=.01
        result=selection.calculate(self.j,self.s,self.basis,self.policy);self.assertTrue(any(not r['geometry_eligible'] for r in result['screening']));self.assertIsNone(result['selected'])

    def test_unknown_missing_or_invalid_candidates_reject(self):
        for action in ['omit','extra','duplicate','nan','zero-reserve']:
            policy=copy.deepcopy(self.policy)
            if action=='omit':policy['nodes'].pop('A')
            if action=='extra':policy['nodes']['unknown']=policy['nodes']['A']
            if action=='duplicate':policy['nodes']['A'].append(policy['nodes']['A'][0])
            if action=='nan':policy['nodes']['A'][0]['penalty']=float('nan')
            if action=='zero-reserve':policy['minimum_remainder_m']['value']=0
            with self.assertRaises(ValueError):selection.calculate(self.j,self.s,self.basis,policy)

    def test_actual_native_geometry_matches_selected_radii(self):
        from bsa.bim import run
        import ifcopenshell
        import ifcopenshell.api as api
        result=selection.calculate(self.j,self.s,self.basis,self.policy);model,fit=compile_model(self.j,self.s,self.basis,result['selected_radii'])
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);source=root/'model.json';source.write_text(json.dumps(model));run(source,root/'bim')
            f=ifcopenshell.open(str(root/'bim/model.ifc'));api.run('spatial.assign_container',f,products=f.by_type('IfcDuctFitting'),relating_structure=f.by_type('IfcBuildingStorey')[0]);f.write(str(root/'intermediate.ifc'));export_storey(root/'intermediate.ifc',root/'selected.ifc')
            checked=inspect_saved(root/'selected.ifc',model);self.assertEqual(checked['body_count'],5);self.assertEqual(checked['actual_links'],4)

if __name__=='__main__':unittest.main()
