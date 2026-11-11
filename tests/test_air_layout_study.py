import json
from pathlib import Path
import unittest
from unittest.mock import patch
from shapely.geometry import box,mapping
from bsa.air_layout_study import evaluate_variant,run
from bsa.cli import digest
from tests import test_allocation_lookup as fixtures


class AirLayoutStudyTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.AllocationLookupTests();f.setUp();self.addCleanup(f.temp.cleanup)
        self.root=f.root;self.project=f.allocation
        self.project['terminals']=[dict(id='A',center_m=[2,2]),dict(id='B',center_m=[8,8])]
        self.boundary=mapping(box(0,0,10,10));self.catalogue=dict(rows=[dict(flow_L_s=1,T025_m=1),dict(flow_L_s=2000,T025_m=8)])
        (self.root/'boundary.json').write_text(json.dumps(self.boundary))
        self.project['boundary_sha256']=digest(self.root/'boundary.json')
        (self.root/'allocation.json').write_text(json.dumps(self.project))
        (self.root/'lookup.json').write_text(json.dumps(f.lookup))
        self.spec=dict(basis='Synthetic layout variants only <unverified>',panel_size_m=[.6,.6],ratio_range=[.0001,10000],references={},
            variants=[dict(id='baseline',basis='Synthetic diagonal centres',changes=[]),dict(id='aligned',basis='Declared position choice',changes=[dict(id='A',center_m=[2,8])])])
        self.study=self.root/'study-input.json';self.study.write_text(json.dumps(self.spec))

    def case(self,variant=None,project=None,boundary=None,catalogue=None):
        return evaluate_variant(boundary or self.boundary,project or self.project,catalogue or self.catalogue,variant or self.spec['variants'][0],[.6,.6],[.0001,10000])

    def test_diagonal_neighbour_is_not_falsely_an_aligned_jet(self):
        baseline=self.case();self.assertGreater(baseline['cell_ray_mismatches'],0)
        east=next(c for c in baseline['cases'] if c['terminal']=='A' and c['direction']=='east')
        self.assertIsNone(east['aligned_midpoint_candidate']);self.assertAlmostEqual(east['screened_length_m'],8)
        self.assertAlmostEqual(east['allocation_cell_ray_distance_m'],6)
        aligned=self.case(self.spec['variants'][1]);self.assertEqual(aligned['cell_ray_mismatches'],0)
        east=next(c for c in aligned['cases'] if c['terminal']=='A' and c['direction']=='east')
        self.assertAlmostEqual(east['screened_length_m'],3)
        self.assertEqual(east['aligned_midpoint_candidate']['terminal'],'B')
        self.assertTrue(aligned['geometric_candidate']);self.assertFalse(aligned['selected'])
        self.assertEqual(baseline['allocation']['checks']['allocated_flow_L_s'],aligned['allocation']['checks']['allocated_flow_L_s'])

    def test_panels_crossing_boundary_or_each_other_remain_issues(self):
        outside=self.case(dict(id='edge',basis='Synthetic edge',changes=[dict(id='A',center_m=[.1,2])]))
        self.assertEqual(outside['panel_outside_boundary'],['A']);self.assertFalse(outside['geometric_candidate'])
        overlap=self.case(dict(id='overlap',basis='Synthetic overlap',changes=[dict(id='B',center_m=[2.1,2])]))
        self.assertTrue(overlap['panel_overlaps']);self.assertFalse(overlap['geometric_candidate'])

    def test_hole_is_boundary_and_outside_catalogue_not_clamped(self):
        boundary=mapping(box(0,0,10,10).difference(box(4,1,6,3)))
        row=self.case(boundary=boundary)
        east=next(c for c in row['cases'] if c['terminal']=='A' and c['direction']=='east')
        self.assertAlmostEqual(east['polygon_ray_distance_m'],2)
        cat=dict(rows=[dict(flow_L_s=3000,T025_m=1),dict(flow_L_s=4000,T025_m=2)])
        self.assertEqual(self.case(catalogue=cat)['diagnostic_ratio_cases_outside_range'],16)

    def test_changed_unknown_or_duplicate_identity_reject(self):
        for changes in ([dict(id='missing',center_m=[1,1])],[dict(id='A',center_m=[1,1])]*2):
            with self.assertRaises(ValueError):self.case(dict(id='bad',basis='Synthetic',changes=changes))
        with self.assertRaises(ValueError):self.case(dict(id='outside',basis='Synthetic',changes=[dict(id='A',center_m=[-1,0])]))

    def test_saved_study_pins_sources_preserves_originals_and_escapes_basis(self):
        before=(self.root/'allocation.json').read_bytes()
        result=run(self.root/'allocation.json',self.root/'lookup.json',self.study,self.root/'output')
        self.assertIsNone(result['selected_variant']);self.assertFalse(result['ADPI_verified'])
        self.assertEqual((self.root/'allocation.json').read_bytes(),before)
        self.assertIn('&lt;unverified&gt;',(self.root/'output/index.html').read_text())
        self.assertTrue(all(digest(Path(p))==sha for p,sha in result['inputs'].items()))
        with self.assertRaises(ValueError):run(self.root/'allocation.json',self.root/'lookup.json',self.study,self.root/'output')

    def test_initial_and_midrun_mutations_reject_without_output(self):
        boundary=self.root/'boundary.json';old=boundary.read_bytes();boundary.write_text('{}')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):run(self.root/'allocation.json',self.root/'lookup.json',self.study,self.root/'bad')
        boundary.write_bytes(old)
        def mutate(*a):
            result=evaluate_variant(*a);boundary.write_bytes(old+b' ');return result
        with patch('bsa.air_layout_study.evaluate_variant',side_effect=mutate),self.assertRaisesRegex(ValueError,'changed during'):
            run(self.root/'allocation.json',self.root/'lookup.json',self.study,self.root/'mutated')
        self.assertFalse((self.root/'mutated').exists())
