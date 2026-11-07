import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.network_design import BASIS
from bsa.network_model_design import GEOMETRY_BASIS,prepare,resize,filter_geometry,run,verify_saved,verify_identities
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    base=ROOT/'examples/network-binding'
    n,m,b=[json.loads((base/(name+'.json')).read_text()) for name in ('network','model','binding')]
    m['project_uuid']='c85f0082-89e6-47e6-8497-d49eb928b533'
    c=dict(sources={'demo':'Synthetic size choices and material scores with explicit size-invariant K; not manufacturer data'},
        options=[dict(id=id,diameter_m=d,roughness_m=.00009,material_score_per_m=score,source='demo')
                 for id,d,score in [('A',.2,1),('B',.4,2),('C',.25,.1)]],
        allowed_options={'MAIN':['A','B','C']},objective='minimise sum(length_m * material_score_per_m)',max_evaluations=10,
        hydraulic_basis=dict(assumption=BASIS,source='demo'))
    g=dict(sources={'demo':'Synthetic explicit outside envelopes; C intentionally exceeds containing space; no inferred wall/clearance'},
        basis=GEOMETRY_BASIS,options={id:dict(outside_diameter_m=d,source='demo') for id,d in [('A',.22),('B',.45),('C',2.)]})
    return n,m,b,c,g


class NetworkModelDesignTests(unittest.TestCase):
    def test_resize_preserves_endpoints_other_devices_and_source(self):
        n,m,b,c,g=inputs();before=copy.deepcopy((n,m,b,c,g));prepare(n,m,b,c,g)
        revised=resize(m,b,{'MAIN':'A'},c,g)
        old=m['devices'][1];new=revised['devices'][1]
        self.assertEqual(new['size_m'],[3,.22,.22]);self.assertEqual(new['properties']['InternalDiameter_m'],.2)
        for port_old,port_new in zip(old['ports'],new['ports']):
            a=[x+y for x,y in zip(old['origin_m'],port_old['offset_m'])]
            z=[x+y for x,y in zip(new['origin_m'],port_new['offset_m'])]
            for x,y in zip(a,z):self.assertAlmostEqual(x,y,places=10)
        for key in ('spaces','systems','connections'):self.assertEqual(m[key],revised[key])
        self.assertEqual(m['devices'][0],revised['devices'][0]);self.assertEqual(m['devices'][2],revised['devices'][2])
        self.assertEqual((n,m,b,c,g),before)
        again=resize(revised,b,{'MAIN':'B'},c,g)
        self.assertEqual(again['devices'][1]['size_m'],[3,.45,.45])
        self.assertNotEqual(again['devices'][1]['source'],new['source'])

    def test_outside_dimensions_required_and_geometric_rejections_retained(self):
        n,m,b,c,g=inputs()
        for mutate in (lambda p:p['options'].pop('A'),lambda p:p['options']['A'].update(outside_diameter_m=.1)):
            bad=copy.deepcopy(g);mutate(bad)
            with self.assertRaises(ProjectError):prepare(n,m,b,c,bad)
        filtered,rejected=filter_geometry(n,m,b,c,g)
        self.assertEqual(filtered['allowed_options']['MAIN'],['A','B'])
        self.assertEqual(rejected[0]['option'],'C');self.assertIn('outside',rejected[0]['reason'])
        self.assertEqual(c['allowed_options']['MAIN'],['A','B','C'])

    def test_multi_piece_chain_and_axis_permutation_keep_world_endpoints(self):
        n,m,b,c,g=inputs();first=m['devices'][1];second=copy.deepcopy(first)
        first['size_m'][0]=1.5;first['ports'][1]['offset_m'][0]=1.5
        second['id']='DUCT2';second['origin_m'][0]=2.5;second['size_m'][0]=1.5;second['ports'][1]['offset_m'][0]=1.5
        m['devices'].append(second);m['connections'][1]['to']='DUCT2.in'
        m['connections'].append(dict(source='demo',**{'from':'DUCT2.out','to':'AT1.in'}));b['segments']['MAIN'].append('DUCT2')
        # Rotate the route axis into Z, testing geometry only, not a vertical air pressure interpretation.
        for space in m['spaces']:
            for key in ('origin_m','size_m'):space[key]=space[key][1:]+space[key][:1]
        for device in m['devices']:
            for key in ('origin_m','size_m'):device[key]=device[key][1:]+device[key][:1]
            for port in device['ports']:port['offset_m']=port['offset_m'][1:]+port['offset_m'][:1]
        prepare(n,m,b,c,g);revised=resize(m,b,{'MAIN':'A'},c,g)
        for old,new in zip(m['devices'],revised['devices']):
            for po,pn in zip(old['ports'],new['ports']):
                for a,z in zip([v+o for v,o in zip(po['offset_m'],old['origin_m'])],[v+o for v,o in zip(pn['offset_m'],new['origin_m'])]):
                    self.assertAlmostEqual(a,z,places=10)
        self.assertEqual(revised['devices'][1]['size_m'],[.22,.22,1.5])

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('fluids'),'requires BIM/network runtimes')
    def test_actual_selected_ifc_pressure_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=inputs();paths=[]
            for name,item in zip(('network','model','binding','catalogue','geometry'),data):
                p=root/(name+'.json');p.write_text(json.dumps(item));paths.append(p)
            hashes=[digest(p) for p in paths];result=run(*paths,root/'run')
            self.assertTrue(result['calculated_checks_pass']);self.assertTrue(result['saved_ifc_resize_checks_pass'])
            self.assertTrue(result['stable_object_port_ids_match'])
            self.assertEqual(result['selected']['choices'],{'MAIN':'A'})
            self.assertEqual(result['original_candidate_count'],3);self.assertEqual(result['geometry_feasible_candidate_count'],2)
            self.assertEqual([digest(p) for p in paths],hashes);self.assertFalse(result['design_accepted'])
            import ifcopenshell
            import ifcopenshell.api as api
            import ifcopenshell.util.element as element
            import ifcopenshell.util.system as system
            native_path=root/'run/selected-coordination/bim/model.ifc';native=ifcopenshell.open(str(native_path))
            baseline=ifcopenshell.open(str(root/'run/baseline-bim/model.ifc'))
            def identities(file):
                rows={d.Name:d.GlobalId for d in file.by_type('IfcDistributionElement')}
                rows.update({d.Name+'.'+p.Name:p.GlobalId for d in file.by_type('IfcDistributionElement') for p in system.get_ports(d)})
                return rows
            self.assertEqual(identities(baseline),identities(native))
            from bsa.bim import run as author
            separate=copy.deepcopy(data[1]);separate['project_uuid']='5ae905a0-a783-4c5c-a1c6-721a35d25711'
            separate_path=root/'separate-project.json';separate_path.write_text(json.dumps(separate))
            author(separate_path,root/'separate-project')
            separate_ifc=ifcopenshell.open(str(root/'separate-project/model.ifc'))
            self.assertTrue(set(identities(baseline).values()).isdisjoint(identities(separate_ifc).values()))
            obj=next(d for d in native.by_type('IfcDuctSegment') if d.Name=='DUCT1');ps=element.get_psets(obj)['BSA_DesignInputs']
            api.run('pset.edit_pset',native,pset=native.by_id(ps['id']),properties={'OutsideDiameter_m':.3});native.write(str(native_path))
            with self.assertRaises(ProjectError):verify_saved(data[1],native_path,data[2],result['selected']['choices'],data[3],data[4])
            obj.GlobalId=ifcopenshell.guid.new();native.write(str(native_path))
            with self.assertRaises(ProjectError):verify_identities(root/'run/baseline-bim/model.ifc',native_path)

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('fluids'),'requires BIM/network runtimes')
    def test_no_contained_geometry_keeps_baseline_and_no_selected_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=inputs();paths=[]
            for row in data[4]['options'].values():row['outside_diameter_m']=2
            for name,item in zip(('network','model','binding','catalogue','geometry'),data):
                p=root/(name+'.json');p.write_text(json.dumps(item));paths.append(p)
            result=run(*paths,root/'run')
            self.assertFalse(result['calculated_checks_pass']);self.assertIsNone(result['selected'])
            self.assertEqual(result['geometry_feasible_candidate_count'],0)
            self.assertTrue((root/'run/baseline-bim/model.ifc').is_file())
            self.assertTrue((root/'run/baseline-analysis/network.json').is_file())
            self.assertFalse((root/'run/selected-model.json').exists())

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('fluids'),'requires BIM/network runtimes')
    def test_workflow_sources_and_changed_selected_ifc_detected(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,item in zip(('network','model','binding','catalogue','geometry'),inputs()):(root/(name+'.json')).write_text(json.dumps(item))
            brief=root/'brief.md';brief.write_text('Resize the selected route and reconcile its saved model.\n')
            task=dict(id='model',kind='network_model_design',project='network.json',model='model.json',binding='binding.json',catalogue='catalogue.json',geometry='geometry.json')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[task],
                requirements=[dict(id='R1',passage='P001',quote='Resize the selected route and reconcile its saved model.',task='model',acceptance='restricted model/calculation consistency')])
            path=root/'plan.json';path.write_text(json.dumps(plan));result=execute(path,root/'run')
            self.assertEqual(result['tasks']['model']['status'],'pass');self.assertTrue(verify(root/'run')['integrity_pass'])
            self.assertIn(str((root/'geometry.json').resolve()),result['inputs'])
            native=root/'run/model/selected-coordination/bim/model.ifc'
            native.write_bytes(native.read_bytes()+b'\n')
            self.assertFalse(verify(root/'run')['integrity_pass'])


if __name__=='__main__':unittest.main()
