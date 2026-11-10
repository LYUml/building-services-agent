import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement

from bsa.rectangular_tee_transitions import run, prepare, inspect
from bsa import rectangular_transition as transition
from bsa.tee_geometry import stable_guid
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class RectangularTeeTransitionsTests(unittest.TestCase):
    def inputs(self, root):
        for source in (ROOT/'examples/rectangular-tee-transitions').glob('*.json'):
            shutil.copyfile(source, root/source.name)
        return root/'project.json', root/'tee.json'

    def test_native_composition_rigid_flow_material_and_saved_controls(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for case in ('two_directed', 'three_oblique_bidirectional'):
                source_dir = root/case; source_dir.mkdir(); project, tee_path = self.inputs(source_dir)
                if case == 'three_oblique_bidirectional':
                    spec = json.loads(tee_path.read_text()); spec['placement'].update(origin_m=[12, -7, 4], rotation=[[.6, 0, .8], [0, 1, 0], [-.8, 0, .6]])
                    spec['port_directions'] = {n: 'SOURCEANDSINK' for n in spec['port_directions']}; tee_path.write_text(json.dumps(spec))
                    data = json.loads(project.read_text()); data['arms']['main-a'] = copy.deepcopy(data['arms']['branch']); project.write_text(json.dumps(data))
                _, data, _, spec, children = prepare(project); before = digest(project)
                result = run(project, root/(case+'-out')); target = root/(case+'-out')/'assembly.ifc'
                self.assertTrue(result['assembly_checks_pass']); self.assertFalse(result['design_accepted'])
                self.assertEqual(digest(project), before)
                self.assertEqual(result['checks']['ports'], 7 if case == 'two_directed' else 9)
                self.assertEqual(result['checks']['connections'], 2 if case == 'two_directed' else 6)
                self.assertEqual(result['checks']['euler_characteristic'], -2)
                self.assertEqual(result['checks']['bore_probe_overlap_m3'], [0, 0])
                self.assertAlmostEqual(result['checks']['material_volume_m3'], .0145245+len(children)*(.00152+.0076*.3732050807568877), places=10)
                self.assertTrue(all(digest(target.parent/name) == sha for name, sha in result['source_artifacts'].items()))
                with self.assertRaisesRegex(ValueError, 'single transition'): transition.inspect(target, children['branch'])
                for mutation in ('gap', 'wall', 'link', 'system', 'extra'):
                    model = ifcopenshell.open(str(target)); child = children['branch']
                    obj = model.by_guid(stable_guid(child, 'IfcDuctFitting', transition.KEY))
                    if mutation == 'gap':
                        matrix = placement.get_local_placement(obj.ObjectPlacement); matrix[0, 3] += .001
                        api.run('geometry.edit_object_placement', model, product=obj, matrix=matrix, is_si=True, should_transform_children=True)
                    elif mutation == 'wall':
                        point = obj.Representation.Representations[0].Items[0].FirstOperand.Outer.CfsFaces[0].Bounds[0].Bound.Polygon[0]
                        x, y, z = point.Coordinates; point.Coordinates = (x+.001, y, z)
                    elif mutation == 'link': model.remove(model.by_type('IfcRelConnectsPorts')[0])
                    elif mutation == 'system': model.by_type('IfcDistributionSystem')[0].IsGroupedBy[0].RelatedObjects = (obj,)
                    else: api.run('root.create_entity', model, ifc_class='IfcDuctSegment', name='Unapproved extra element')
                    bad = root/(case+'-'+mutation+'.ifc'); model.write(str(bad))
                    with self.subTest(case=case, mutation=mutation), self.assertRaises(ValueError): inspect(bad, spec, data, children)

    def test_explicit_source_arms_and_failed_upstream_length(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); project, _ = self.inputs(root); original = json.loads(project.read_text())
            for case in ('missing', 'bare', 'outside', 'unsourced'):
                data = copy.deepcopy(original)
                if case == 'missing': del data['arms']['branch']
                elif case == 'bare': data['arms'] = {n: {'kind': 'bare'} for n in data['arms']}
                elif case == 'outside': data['tee'] = '../outside.json'
                else: data['source'] = ''
                project.write_text(json.dumps(data))
                with self.subTest(case=case), self.assertRaises(ValueError): prepare(project)
            original['arms']['main-b']['transition_length_m'] += .001; project.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, 'length differs'): run(project, root/'failed')
            self.assertFalse((root/'failed/assembly.ifc').exists())
            self.assertTrue((root/'failed/main-b/upstream.log').exists())
