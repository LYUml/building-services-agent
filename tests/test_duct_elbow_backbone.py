import copy
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.api as api
from bsa.duct_elbow_backbone import compile_model,inspect_saved
from bsa.duct_backbone_ifc import export_storey
from bsa.bim import run
from bsa.duct_junction_review import inspect
from bsa.duct_equivalent import calculate
from tests import test_duct_backbone_ifc as fixtures

ROOT=Path(__file__).resolve().parents[1]


class DuctElbowBackboneTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.DuctBackboneIFCTests();fixture.setUp();self.j=fixture.junction;self.s=fixture.schedule;self.basis=fixture.basis
        self.radii={'Q':dict(radius_m=.3,classification='assumed',source='Synthetic finite elbow radius only')}

    def test_trimmed_stations_source_flow_and_exact_links(self):
        model,fit=compile_model(self.j,self.s,self.basis,self.radii)
        self.assertEqual(fit['authored_elbow_nodes'],['Q']);self.assertEqual(fit['blocked_elbow_nodes'],{})
        self.assertEqual(len(model['devices']),6);self.assertEqual(len(model['connections']),2)
        rows={d['id']:d for d in model['devices']};self.assertAlmostEqual(rows['S3']['size_m'][0],1.7);self.assertAlmostEqual(rows['S4']['size_m'][1],1.7)
        self.assertAlmostEqual(rows['BEND-Q']['properties']['CenterlineRadius_m'],.3)
        self.assertFalse(fit['full_fitting_trim_complete'])
        self.assertIn('P',fit['remaining_nonelbow_junction_nodes'])
        self.assertIn(dict(node='P',requirement='transition_required'),fit['remaining_source_connection_nodes'])

    def test_two_end_budget_blocks_all_responsible_corners_without_shortening_radii(self):
        import ezdxf
        doc=ezdxf.new();doc.units=6;points=dict(R=[-3,0,0],A=[0,0,0],B=[0,1,0],Z=[3,1,0]);entries={};edges=[];rows=[]
        for id,a,b in [('S0','R','A'),('S1','A','B'),('S2','B','Z')]:
            line=doc.modelspace().add_line(points[a],points[b]);entries[id]=dict(line_handle=line.dxf.handle,from_node=a,to_node=b,from_m=points[a],to_m=points[b]);edges.append(dict(id=id,**{'from':a,'to':b}))
            inputs=dict(width_m=.6,height_m=.3,flow_m3_s=.5);rows.append(dict(id=id,inputs=inputs,calculation=calculate(**inputs,**self.s['air']),failures=[]))
        s=dict(status='pass',air=self.s['air'],sections=rows,flow_aggregation=dict(root='R',sections=edges,section_flow_L_s={e['id']:500 for e in edges},leaf_flow_L_s={'Z':500},total_flow_L_s=500,topology_pass=True,flow_conserved=True,basis='Synthetic zigzag'))
        j=inspect(doc,s,dict(basis='Synthetic binding',sections=entries));radii={n:dict(radius_m=.9,classification='assumed',source='Synthetic radius') for n in ('A','B')}
        model,fit=compile_model(j,s,self.basis,radii)
        self.assertEqual(set(fit['blocked_elbow_nodes']),{'A','B'});self.assertEqual(fit['authored_elbow_nodes'],[])
        budget=next(b for b in fit['source_section_budgets'] if b['section']=='S1');self.assertAlmostEqual(budget['remaining_after_declared_elbows_m'],-.8)
        self.assertEqual(radii['A']['radius_m'],.9);self.assertEqual(len(model['devices']),3)

    def test_missing_inventory_and_geometry_radius_failures_remain_explicit(self):
        with self.assertRaises(ValueError):compile_model(self.j,self.s,self.basis,{})
        radii=copy.deepcopy(self.radii);radii['Q']['radius_m']=.01
        model,fit=compile_model(self.j,self.s,self.basis,radii)
        self.assertIn('Q',fit['blocked_elbow_nodes']);self.assertEqual(len(model['devices']),5)

    def test_actual_saved_native_bend_connections_and_link_tampering(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            root=Path(temp);model,fit=compile_model(self.j,self.s,self.basis,self.radii);source=root/'model.json';source.write_text(json.dumps(model));result=run(source,root/'bim')
            self.assertTrue(result['model_checks_pass']);file=ifcopenshell.open(str(root/'bim/model.ifc'));api.run('spatial.assign_container',file,products=file.by_type('IfcDuctFitting'),relating_structure=file.by_type('IfcBuildingStorey')[0]);file.write(str(root/'intermediate.ifc'))
            export_storey(root/'intermediate.ifc',root/'final.ifc');check=inspect_saved(root/'final.ifc',model)
            self.assertEqual((check['body_count'],check['owned_ports'],check['actual_links']),(6,12,2))
            file=ifcopenshell.open(str(root/'final.ifc'));file.remove(file.by_type('IfcRelConnectsPorts')[0]);file.write(str(root/'bad.ifc'))
            with self.assertRaisesRegex(ValueError,'logical links'):inspect_saved(root/'bad.ifc',model)
