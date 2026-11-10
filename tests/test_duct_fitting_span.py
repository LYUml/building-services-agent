from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement
import numpy as np

from bsa.duct_fitting_span import calculate, author, inspect, material_intersections, run
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class DuctFittingSpanTests(unittest.TestCase):
    def test_changed_native_source_during_authoring_blocks_result(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); native = root/'native-source.txt'; native.write_text('original')
            for name in ('plan.json', 'a.json', 'b.json', 'a-binding.json', 'b-binding.json'): (root/name).write_text('{}')
            for name in ('workflow', 'a-model', 'b-model'): (root/name).mkdir()
            data = dict(project_uuid='50b5bb41-5042-4933-a4fe-077181945095', source='Synthetic handoff control only', plan='plan.json', workflow='workflow', native_task='native', section='S',
                endpoints=[dict(project='a.json', model='a-model', binding='a-binding.json'), dict(project='b.json', model='b-model', binding='b-binding.json')])
            project = root/'project.json'; project.write_text(json.dumps(data))
            def fitting_review(*args):
                directory = args[-1]; directory.mkdir()
                (directory/'junction-review.json').write_text(json.dumps({'inputs': {str(native): digest(native)}}))
                return dict(plan_extent_check_pass=True, inputs={})
            def changed_author(data, span, target):
                native.write_text('changed during generation'); target.write_text('unit provenance control, not IFC')
                return {}
            with patch('bsa.duct_fitting_span.duct_fitting_fit.run', side_effect=fitting_review), patch('bsa.duct_fitting_span.endpoint', side_effect=self.fixture()), patch('bsa.duct_fitting_span.author', side_effect=changed_author), patch('bsa.duct_fitting_span.material_intersections', return_value={'no_material_interpenetration': True}), patch('bsa.workflow.verify', return_value={'integrity_pass': True}):
                with self.assertRaisesRegex(ValueError, 'changed during generation'): run(project, root/'out')
            self.assertFalse((root/'out/span.json').exists())
            calls = []
            def changed_between_reviews(*args):
                calls.append(1)
                if len(calls) == 2: native.write_text('different endpoint context')
                return fitting_review(*args)
            with patch('bsa.duct_fitting_span.duct_fitting_fit.run', side_effect=changed_between_reviews), patch('bsa.duct_fitting_span.endpoint', side_effect=self.fixture()):
                with self.assertRaisesRegex(ValueError, 'changed between endpoint'): run(project, root/'mixed')
            self.assertFalse((root/'mixed/span.ifc').exists())

    def fixture(self, oblique=False):
        a = np.eye(4); a[:3, 3] = [12, -7, 4]
        if oblique: a[:3, :3] = [[.6, 0, .8], [0, 1, 0], [-.8, 0, .6]]
        b = a.copy(); b[:3, 1:3] *= -1; b[:3, 3] = a[:3, 3]+6.5*a[:3, 2]
        common = dict(width_m=.5, height_m=.3, wall_thickness_m=.005, source_length_m=10, model_sha256='synthetic-hash')
        return [dict(common, node='A', port_guid='synthetic-source-port', frame=a, flow_direction='SOURCE', reach_m=1.5, model_ifc='synthetic-a.ifc'),
                dict(common, node='B', port_guid='synthetic-sink-port', frame=b, flow_direction='SINK', reach_m=2., model_ifc='synthetic-b.ifc')]

    def test_two_end_trim_roll_direction_and_overrun(self):
        for reverse in (False, True):
            ends = self.fixture(True)
            span = calculate(ends[::-1] if reverse else ends)
            self.assertEqual(span['length_m'], 10-1.5-2)
            self.assertEqual(span['upstream_node'], 'A'); self.assertEqual(span['downstream_node'], 'B')
            self.assertTrue(span['straight_available']); self.assertFalse(span['design_accepted'])
        for case in ('size', 'wall', 'roll', 'off_ray', 'flow', 'same_node', 'length'):
            ends = self.fixture()
            if case == 'size': ends[1]['width_m'] += .01
            elif case == 'wall': ends[1]['wall_thickness_m'] += .001
            elif case == 'roll': ends[1]['frame'][:3, :2] = ends[1]['frame'][:3, [1, 0]]
            elif case == 'off_ray': ends[1]['frame'][0, 3] += .001
            elif case == 'flow': ends[1]['flow_direction'] = 'SOURCE'
            elif case == 'same_node': ends[1]['node'] = 'A'
            else: ends[1]['source_length_m'] += .001
            with self.subTest(case=case), self.assertRaises(ValueError): calculate(ends)
        ends = self.fixture()
        for e in ends: e['source_length_m'] = 3
        failed = calculate(ends)
        self.assertFalse(failed['straight_available']); self.assertEqual(failed['status'], 'fail'); self.assertEqual(failed['length_m'], -.5)

    def test_saved_native_wall_frames_and_mutations(self):
        data = dict(project_uuid='50b5bb41-5042-4933-a4fe-077181945095', source='Explicit synthetic span test; not installed length', section='S')
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for oblique in (False, True):
                span = calculate(self.fixture(oblique)); target = root/(str(oblique)+'.ifc')
                result = author(data, span, target)
                self.assertAlmostEqual(result['wall_volume_m3'], .05265, places=10)
                self.assertEqual(result['euler_characteristic'], 0); self.assertEqual(result['ports'], 2)
                self.assertFalse(result['external_logical_connections_created'])
                overlap = material_intersections(target, [{'model_ifc': str(target)}])
                self.assertFalse(overlap['no_material_interpenetration'])
                self.assertAlmostEqual(overlap['pairs'][0]['overlap_volume_m3'], .05265, places=10)
                model = ifcopenshell.open(str(target)); obj = model.by_type('IfcDuctSegment')[0]
                matrix = placement.get_local_placement(obj.ObjectPlacement); matrix[0, 3] += 100
                api.run('geometry.edit_object_placement', model, product=obj, matrix=matrix, is_si=True)
                outside = root/(str(oblique)+'-outside.ifc'); model.write(str(outside))
                self.assertTrue(material_intersections(target, [{'model_ifc': str(outside)}])['no_material_interpenetration'])
                for case in ('length', 'wall_shift', 'port', 'source', 'connection'):
                    model = ifcopenshell.open(str(target)); obj = model.by_type('IfcDuctSegment')[0]
                    if case == 'length': obj.Representation.Representations[0].Items[0].Depth += .001
                    elif case == 'wall_shift': obj.Representation.Representations[0].Items[0].Position.Location.Coordinates = (.001, 0., 0.)
                    elif case == 'port':
                        port = model.by_type('IfcDistributionPort')[0]; matrix = placement.get_local_placement(port.ObjectPlacement); matrix[0, 3] += .001
                        api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
                    elif case == 'source':
                        pset = model.by_type('IfcPropertySet')[0]; api.run('pset.edit_pset', model, pset=pset, properties={'Source': 'changed'})
                    else:
                        ports = model.by_type('IfcDistributionPort'); api.run('system.connect_port', model, port1=ports[0], port2=ports[1], direction='SOURCE')
                    bad = root/(str(oblique)+'-'+case+'.ifc'); model.write(str(bad))
                    with self.subTest(oblique=oblique, case=case), self.assertRaises(ValueError): inspect(bad, data, span)
