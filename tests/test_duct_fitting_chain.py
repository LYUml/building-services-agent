import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement
import numpy as np

from bsa import rectangular_tee_transitions as composition
from bsa import rectangular_transition as transition
from bsa import duct_fitting_span as span_tool
from bsa.duct_fitting_chain import merge, inspect, snapshot, solve_frames
from bsa.tee_geometry import stable_guid
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class DuctFittingChainTests(unittest.TestCase):
    def sources(self, root, oblique):
        root.mkdir(); angle = math.radians(15); a = np.eye(4)
        if oblique:
            a[:3, :3] = [[.6, 0, .8], [0, 1, 0], [-.8, 0, .6]]; a[:3, 3] = [12, -7, 4]
        paths = []; values = []; projects = []
        for name, width, height, reach, end, z, uid in [('a', .6, .3, .7, [.4, .2], 0, 'c3cb2718-c884-452d-ac69-f52d02b327ba'), ('b', .4, .2, .5, [.3, .15], 4, 'a7d219a9-5579-4d63-b131-2813384f6651')]:
            directory = root/name; directory.mkdir()
            spec = json.loads((ROOT/'examples/rectangular-tee-transitions/tee.json').read_text())
            matrix = a.copy(); matrix[:3, 3] += z*a[:3, 2]
            spec.update(project_uuid=uid, internal_width_m=width, internal_height_m=height, main_half_length_m=reach, branch_length_m=reach)
            spec['placement'].update(origin_m=matrix[:3, 3].tolist(), rotation=matrix[:3, :3].tolist())
            (directory/'tee.json').write_text(json.dumps(spec))
            arm = dict(kind='transition', end_section_m=end, start_length_m=.1, end_length_m=.1, upstream_angle_degrees=30,
                transition_length_m=max(abs(width-end[0]), abs(height-end[1]))/(2*math.tan(angle)))
            data = dict(source='Explicit synthetic chain test', classification='assumed', tee='tee.json', arms={'main-a': {'kind': 'bare'}, 'main-b': arm, 'branch': arm})
            project = directory/'project.json'; project.write_text(json.dumps(data)); projects.append(project)
            result = composition.run(project, directory/'model'); paths.append(directory/'model/assembly.ifc'); values.append(result['checks']['independent_material_volume_m3'])
        ends = []
        for i, arm in enumerate(('main-b', 'main-a')):
            _, _, _, spec, children = composition.prepare(projects[i]); child = children.get(arm)
            guid = stable_guid(child, 'IfcDistributionPort', transition.KEY, 'end') if child else stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', arm)
            model = ifcopenshell.open(str(paths[i])); port = model.by_guid(guid)
            reach = .7+.2+.2/(2*math.tan(angle)) if i == 0 else .5
            ends.append(dict(node=str(i), port_guid=guid, frame=placement.get_local_placement(port.ObjectPlacement), flow_direction=port.FlowDirection,
                width_m=.4, height_m=.2, wall_thickness_m=.005, source_length_m=4., reach_m=reach, model_ifc=str(paths[i]), model_sha256=digest(paths[i])))
        span = span_tool.calculate(ends)
        data = dict(project_uuid='fa906ee8-d17a-41e6-82e6-c86635521867', source='Explicit synthetic chain source', section='S')
        target = root/'span.ifc'; checks = span_tool.author(data, span, target); values.append(checks['independent_wall_volume_m3']); paths.append(target)
        return paths, data, span, sum(values)

    def test_native_merge_preserves_sources_and_rejects_saved_mutations(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for oblique in (False, True):
                paths, data, span, volume = self.sources(root/str(oblique), oblique); pins = {p: digest(p) for p in paths}
                target = root/(str(oblique)+'-chain.ifc'); checks, expected = merge(paths, target, data, span, volume)
                self.assertEqual(checks['components'], 7); self.assertEqual(checks['ports'], 16)
                self.assertEqual(checks['directed_interfaces'], 6); self.assertEqual(checks['boundary_ports'], 4)
                self.assertEqual(checks['euler_characteristic'], -4); self.assertTrue(checks['one_connected_material'])
                self.assertEqual(checks['material_pair_count'], 21); self.assertFalse(checks['design_accepted'])
                self.assertTrue(all(digest(p) == sha for p, sha in pins.items()))
                for case in ('link', 'body', 'pose', 'port', 'system', 'extra'):
                    model = ifcopenshell.open(str(target))
                    if case == 'link': model.remove(model.by_type('IfcRelConnectsPorts')[0])
                    elif case == 'body': model.by_type('IfcDuctSegment')[0].Representation.Representations[0].Items[0].Depth += .001
                    elif case == 'pose':
                        obj = model.by_type('IfcDuctSegment')[0]; matrix = placement.get_local_placement(obj.ObjectPlacement); matrix[0, 3] += .001
                        api.run('geometry.edit_object_placement', model, product=obj, matrix=matrix, is_si=True, should_transform_children=True)
                    elif case == 'port':
                        port = model.by_type('IfcDistributionPort')[0]; matrix = placement.get_local_placement(port.ObjectPlacement); matrix[0, 3] += .001
                        api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
                    elif case == 'system':
                        relation = model.by_type('IfcDistributionSystem')[0].IsGroupedBy[0]; relation.RelatedObjects = relation.RelatedObjects[:-1]
                    else: api.run('root.create_entity', model, ifc_class='IfcBuildingElementProxy', name='Unapproved extra')
                    bad = root/(str(oblique)+'-'+case+'.ifc'); model.write(str(bad))
                    with self.subTest(oblique=oblique, case=case), self.assertRaises(ValueError): inspect(bad, data, expected)
                malformed = copy.deepcopy(expected); malformed['links'] = malformed['links'][:-1]
                with self.assertRaises(ValueError): solve_frames(malformed)
                bad_source = ifcopenshell.open(str(paths[0])); port = bad_source.by_type('IfcDistributionPort')[0]
                matrix = placement.get_local_placement(port.ObjectPlacement); matrix[0, 3] += .001
                api.run('geometry.edit_object_placement', bad_source, product=port, matrix=matrix, is_si=True)
                bad_path = root/(str(oblique)+'-source-port.ifc'); bad_source.write(str(bad_path))
                with self.assertRaisesRegex(ValueError, 'native cap'): snapshot([bad_path]+paths[1:])
