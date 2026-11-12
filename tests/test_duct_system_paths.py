import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_duct_junction_review as fixtures
from bsa.duct_junction_review import inspect
from bsa.duct_equivalent import calculate as friction
from bsa.duct_system_paths import calculate,run
from bsa.cli import digest

ROOT=Path(__file__).resolve().parents[1]


class DuctSystemPathsTests(unittest.TestCase):
    def test_external_output_requires_host_selection_and_stays_outside_workflow(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();plan=root/'plan.json';workflow=root/'workflow'
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':''}):
                with self.assertRaisesRegex(ValueError,'host-selected'):
                    run(plan,workflow,'native',root/'out')
            with patch.dict(os.environ,{'BSA_PROJECT_ROOT':str(root)}):
                for out in (workflow/'nested',root,root.parent/'unselected-path-study'):
                    with self.assertRaisesRegex(ValueError,'outside source workflow'):
                        run(plan,workflow,'native',out)

    def source(self):
        doc,schedule,binding=fixtures.DuctJunctionReviewTests().fixture()
        schedule['air']=dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=9e-5)
        for row in schedule['sections']:row['calculation']=friction(**row['inputs'],**schedule['air'])
        return inspect(doc,schedule,binding),schedule

    def test_whole_tree_paths_and_untrimmed_scope(self):
        junction,schedule=self.source();r=calculate(junction,schedule);paths={p['outlet_node']:p for p in r['paths']};sections={s['id']:s for s in r['sections']}
        self.assertEqual(r['section_count'],5);self.assertEqual(r['node_count'],6);self.assertEqual(r['outlet_path_count'],2)
        self.assertAlmostEqual(r['inlet_flow_m3_s'],.5);self.assertAlmostEqual(r['outlet_flow_m3_s'],.5)
        self.assertEqual(paths['B']['section_ids'],['S0','S2']);self.assertEqual(paths['L']['section_ids'],['S0','S1','S3','S4'])
        self.assertAlmostEqual(paths['B']['source_centreline_length_m'],4);self.assertAlmostEqual(paths['L']['source_centreline_length_m'],8)
        original={s['id']:s for s in schedule['sections']}
        for path in paths.values():
            expected=sum(2*original[s]['calculation']['friction_Pa_m'] for s in path['section_ids'])
            self.assertAlmostEqual(path['nominal_centreline_friction_Pa'],expected)
            self.assertIsNone(path['complete_total_pressure_drop_Pa'])
        self.assertAlmostEqual(sum(p['nominal_centreline_friction_Pa'] for p in paths.values())-sum(s['nominal_centreline_friction_Pa'] for s in sections.values()),sections['S0']['nominal_centreline_friction_Pa'])
        self.assertTrue(all(s['physical_straight_length_m'] is None and s['physical_straight_friction_Pa'] is None for s in sections.values()))
        self.assertIsNone(r['fan_critical_path']);self.assertFalse(r['pressure_budget_complete']);self.assertFalse(r['design_accepted'])
        for bad in ('friction','length','edge','total','leaf','cycle','coverage'):
            j,s=copy.deepcopy(junction),copy.deepcopy(schedule)
            if bad=='friction':s['sections'][0]['calculation']['friction_Pa_m']*=2
            elif bad=='length':j['nodes'][0]['incidents'][0]['source_centreline_length_m']+=1
            elif bad=='edge':s['flow_aggregation']['sections'][0]['from'],s['flow_aggregation']['sections'][0]['to']='J','R'
            elif bad=='total':s['flow_aggregation']['total_flow_L_s']=600
            elif bad=='leaf':s['flow_aggregation']['leaf_flow_L_s']['extra']=1
            elif bad=='cycle':s['flow_aggregation']['sections'][-1]['to']='J'
            else:s['sections'].append(copy.deepcopy(s['sections'][0]))
            with self.subTest(bad=bad),self.assertRaises(ValueError):calculate(j,s)

    def test_source_mutation_blocks_final_report(self):
        # Source-boundary control only;actual native source execution is separate.
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);workflow=root/'workflow';(workflow/'sizing').mkdir(parents=True)
            plan=root/'plan.json';plan.write_text('{}');source=root/'source.txt';source.write_text('Original')
            j,s=self.source();saved=workflow/'sizing/results.json';saved.write_text(json.dumps(s))
            record=dict(inputs={str(plan):digest(plan),str(source):digest(source)},artifact_hashes={'sizing/results.json':digest(saved)},requirements=[])
            (workflow/'workflow.json').write_text(json.dumps(record))
            def reviewed(plan,workflow,native_task,output):
                output.parent.mkdir(parents=True);output.write_text('{}')
                return dict(j,lineage=['native','sheet','sizing'],inputs={str(source):digest(source)})
            def changed(j,s):
                r=calculate(j,s);source.write_text('Changed during study');return r
            with patch('bsa.delivery.context',return_value=({},record,dict(integrity_pass=True))),patch('bsa.duct_system_paths.from_workflow',side_effect=reviewed),patch('bsa.duct_system_paths.calculate',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):run(plan,workflow,'native',root/'out')
            self.assertFalse((root/'out/system-paths.json').exists())
