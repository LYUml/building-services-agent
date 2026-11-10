import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bsa.duct_fitting_fit import assess
from bsa.rectangular_tee_transitions import prepare
from bsa.rectangular_tee import port_frames

ROOT = Path(__file__).resolve().parents[1]


class DuctFittingFitTests(unittest.TestCase):
    def fixture(self, root):
        for source in (ROOT/'examples/rectangular-tee-transitions').glob('*.json'):
            shutil.copyfile(source, root/source.name)
        tee_path = root/'tee.json'; spec = json.loads(tee_path.read_text())
        spec['placement'].update(origin_m=[5, 7, 3], rotation=[[0, 0, -1], [-1, 0, 0], [0, 1, 0]])
        tee_path.write_text(json.dumps(spec)); _, data, _, spec, children = prepare(root/'project.json')
        frames = port_frames(spec); mapping = {n: 'S-'+n for n in frames}
        incidents = [dict(section=mapping[n], role='incoming' if n == 'main-a' else 'outgoing',
            line_handle='source-'+n, outward_unit_vector=f[:3, 2].tolist(), source_centreline_length_m=2,
            width_m=(children[n]['end_section_m'][0] if n in children else .6),
            height_m=(children[n]['end_section_m'][1] if n in children else .3)) for n, f in frames.items()]
        review = dict(source_correspondence_pass=True, nodes=[dict(node='J', degree=3, point_m=[5, 7, 0], incidents=incidents)])
        return review, spec, children, dict(source='Synthetic binding', node='J', arms=mapping)

    def test_independent_reaches_overrun_and_unverified_installation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            review, spec, children, binding = self.fixture(Path(tmp)); result = assess(review, spec, children, binding)
            rows = {r['arm']: r for r in result['arms']}
            self.assertAlmostEqual(rows['main-a']['outward_reach_m'], .7)
            self.assertAlmostEqual(rows['main-b']['outward_reach_m'], .7+.2+.3732050807568877)
            self.assertAlmostEqual(rows['branch']['remaining_centreline_m'], 2-.6-.2-.3732050807568877)
            self.assertTrue(result['plan_extent_check_pass']); self.assertFalse(result['design_accepted'])
            self.assertFalse(result['installation_elevation_verified']); self.assertFalse(result['neighbouring_end_fitting_trim_verified'])
            self.assertFalse(result['section_roll_verified'])
            review['nodes'][0]['incidents'][2]['source_centreline_length_m'] = .5
            result = assess(review, spec, children, binding)
            self.assertFalse(result['plan_extent_check_pass']); self.assertEqual(result['status'], 'fail')
            self.assertLess(result['arms'][2]['remaining_centreline_m'], 0)

    def test_mismatch_and_incomplete_bindings_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            original = self.fixture(Path(tmp))
            for case in ('size', 'ray', 'origin', 'direction', 'mapping', 'degree', 'unverified'):
                review, spec, children, binding = copy.deepcopy(original)
                if case == 'size': review['nodes'][0]['incidents'][1]['width_m'] += .01
                elif case == 'ray': review['nodes'][0]['incidents'][1]['outward_unit_vector'] = [0, 1, 0]
                elif case == 'origin': spec['placement']['origin_m'][0] += .001
                elif case == 'direction': spec['port_directions']['main-a'] = 'SOURCE'
                elif case == 'mapping': binding['arms']['branch'] = binding['arms']['main-b']
                elif case == 'degree': review['nodes'][0]['degree'] = 4
                else: review['source_correspondence_pass'] = False
                with self.subTest(case=case), self.assertRaises(ValueError): assess(review, spec, children, binding)
