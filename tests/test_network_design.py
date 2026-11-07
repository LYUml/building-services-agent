import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.network_design import BASIS,search,run,validate_catalogue
from bsa.cli import digest


def inputs():
    source='Synthetic laminar fully-filled pipe and material points, not product data or money'
    project=dict(name='Synthetic discrete pipe sizing',model='steady incompressible circular tree',sources={'demo':source},
        fluid=dict(density_kg_m3=1000,dynamic_viscosity_pa_s=.001,source='demo'),
        supply=dict(node='P',total_pressure_pa=10,source='demo'),
        nodes=[dict(id='P',elevation_m=0,demand_m3_s=0,required_total_pressure_pa=0,source='demo'),
               dict(id='T',elevation_m=0,demand_m3_s=1e-6,required_total_pressure_pa=0,source='demo')],
        segments=[dict(id='PIPE',**{'from':'P','to':'T'},diameter_m=.01,length_m=10,roughness_m=0,minor_k=0,max_velocity_m_s=1,source='demo')])
    catalogue=dict(sources={'demo':source},options=[dict(id=id,diameter_m=d,roughness_m=0,material_score_per_m=score,source='demo')
                  for id,d,score in [('D10',.01,1),('D20',.02,2)]],allowed_options={'PIPE':['D10','D20']},
        objective='minimise sum(length_m * material_score_per_m)',max_evaluations=10,
        hydraulic_basis=dict(assumption=BASIS,source='demo'))
    return project,catalogue


class NetworkDesignTests(unittest.TestCase):
    def test_independent_poiseuille_feasibility_and_minimum_score(self):
        project,catalogue=inputs();before=copy.deepcopy((project,catalogue))
        result,selected=search(project,catalogue)
        self.assertEqual((project,catalogue),before)
        self.assertEqual(result['selected']['choices'],{'PIPE':'D20'})
        self.assertEqual(result['selected']['material_score'],20)
        self.assertEqual(result['feasible_count'],1)
        for row,d in zip(result['candidates'],[.01,.02]):
            expected=128*.001*10*1e-6/(math.pi*d**4)
            self.assertAlmostEqual(row['required_source_total_pressure_pa'],expected,places=10)
        for key in ('fluid','supply','nodes'):self.assertEqual(selected[key],project[key])
        for key in ('length_m','minor_k','max_velocity_m_s','from','to'):
            self.assertEqual(selected['segments'][0][key],project['segments'][0][key])

    def test_no_feasible_design_and_transitional_candidate_retained(self):
        project,catalogue=inputs();project['supply']['total_pressure_pa']=0
        result,selected=search(project,catalogue)
        self.assertIsNone(selected);self.assertFalse(result['feasible_design_found'])
        self.assertEqual(result['evaluated_count'],2)
        project['supply']['total_pressure_pa']=100;project['nodes'][1]['demand_m3_s']=2e-5
        result,selected=search(project,catalogue)
        self.assertIn('transitional',result['candidates'][0]['analysis_error'])
        self.assertEqual(result['selected']['choices']['PIPE'],'D20')

    def test_deterministic_ties_and_search_limits(self):
        project,catalogue=inputs();project['supply']['total_pressure_pa']=100
        catalogue['options'][1].update(diameter_m=.01,material_score_per_m=1)
        result,_=search(project,catalogue)
        self.assertEqual(result['selected']['choices']['PIPE'],'D10')
        catalogue['options'].reverse();catalogue['allowed_options']['PIPE'].reverse()
        again,_=search(project,catalogue);self.assertEqual(result['candidates'],again['candidates'])
        catalogue['max_evaluations']=1
        with self.assertRaises(ProjectError):search(project,catalogue)

    def test_invalid_catalogues_rejected(self):
        project,catalogue=inputs()
        for mutate in (lambda c:c.update(allowed_options={}),lambda c:c['allowed_options']['PIPE'].append('missing'),
                       lambda c:c['options'][0].update(material_score_per_m=float('nan')),
                       lambda c:c['hydraulic_basis'].update(assumption='silently change all demands'),
                       lambda c:c['options'].append(copy.deepcopy(c['options'][0]))):
            candidate=copy.deepcopy(catalogue);mutate(candidate)
            with self.assertRaises(ProjectError):validate_catalogue(project,candidate)

    @unittest.skipUnless(importlib.util.find_spec('fluids'),'requires network runtime')
    def test_actual_baseline_failure_selected_rerun_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);project,catalogue=inputs();paths=[]
            for name,data in (('project',project),('catalogue',catalogue)):
                path=root/(name+'.json');path.write_text(json.dumps(data));paths.append(path)
            hashes=[digest(p) for p in paths];result=run(*paths,root/'run')
            self.assertFalse(result['baseline']['calculated_checks_pass'])
            self.assertTrue(result['selected_rerun_pass']);self.assertTrue(result['search_complete'])
            self.assertEqual([digest(p) for p in paths],hashes)
            baseline=json.loads((root/'run/baseline/network.json').read_text())
            selected=json.loads((root/'run/selected/network.json').read_text())
            self.assertFalse(baseline['calculated_checks_pass']);self.assertTrue(selected['calculated_checks_pass'])
            self.assertFalse(result['design_accepted'])

    @unittest.skipUnless(importlib.util.find_spec('fluids'),'requires turbulent network runtime')
    def test_branched_catalogue_choice_matches_independent_velocity_lower_bound(self):
        root=Path(__file__).resolve().parents[1]/'examples/network-design'
        project=json.loads((root/'project.json').read_text());catalogue=json.loads((root/'catalogue.json').read_text())
        result,selected=search(project,catalogue)
        options={o['id']:o for o in catalogue['options']}
        flows={'MAIN':.5,'BR-A':.2,'BR-B':.3}
        lower_bound={s['id']:min((id for id in catalogue['allowed_options'][s['id']] if options[id]['diameter_m']>=math.sqrt(4*flows[s['id']]/(math.pi*s['max_velocity_m_s']))),
                    key=lambda id:options[id]['material_score_per_m']) for s in project['segments']}
        self.assertEqual(result['selected']['choices'],lower_bound)
        self.assertEqual(result['candidate_count'],125);self.assertTrue(result['search_complete'])
        self.assertEqual(result['selected']['material_score'],63)
        self.assertLessEqual(result['selected']['required_source_total_pressure_pa'],project['supply']['total_pressure_pa'])

    @unittest.skipUnless(importlib.util.find_spec('fluids'),'requires network runtime')
    def test_workflow_success_failure_and_integrity(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);project,catalogue=inputs()
            (root/'project.json').write_text(json.dumps(project));(root/'catalogue.json').write_text(json.dumps(catalogue))
            brief=root/'brief.md';brief.write_text('Compare all supplied pipe choices and retain failures.\n')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},
                tasks=[dict(id='sizing',kind='network_design',project='project.json',catalogue='catalogue.json')],
                requirements=[dict(id='R1',passage='P001',quote='Compare all supplied pipe choices and retain failures.',task='sizing',acceptance='complete conditional design comparison')])
            path=root/'plan.json';path.write_text(json.dumps(plan));report=execute(path,root/'run')
            self.assertEqual(report['tasks']['sizing']['status'],'pass');self.assertTrue(verify(root/'run')['integrity_pass'])
            self.assertIn(str((root/'catalogue.json').resolve()),report['inputs'])
            selected=root/'run/sizing/selected-network.json';selected.write_text('{}')
            self.assertFalse(verify(root/'run')['integrity_pass'])
            project['supply']['total_pressure_pa']=0;(root/'project.json').write_text(json.dumps(project))
            failed=execute(path,root/'failed')
            self.assertEqual(failed['tasks']['sizing']['status'],'fail')
            self.assertTrue((root/'failed/sizing/design-comparison.json').exists())
            self.assertFalse((root/'failed/sizing/selected-network.json').exists())


if __name__=='__main__':unittest.main()
