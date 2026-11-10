import json
import math
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement

from bsa.rectangular_transition import run, inspect, validate
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class RectangularTransitionTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT/'examples/rectangular-transition/project.json').read_text())

    def test_saved_native_geometry_ports_moments_and_mutations(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            for case in ('reduction', 'expansion', 'cross_oblique'):
                data = self.fixture()
                if case == 'expansion':
                    data['start_section_m'], data['end_section_m'] = data['end_section_m'], data['start_section_m']
                    data['port_directions'] = {'start': 'SOURCEANDSINK', 'end': 'SOURCEANDSINK'}
                elif case == 'cross_oblique':
                    data.update(start_section_m=[.5, .2], end_section_m=[.35, .3], upstream_angle_degrees=45,
                                transition_length_m=.075/math.tan(math.radians(22.5)))
                    data['placement'].update(origin_m=[12, -7, 4], rotation=[[.6, 0, .8], [0, 1, 0], [-.8, 0, .6]])
                project = root/(case+'.json'); project.write_text(json.dumps(data)); before = digest(project)
                result = run(project, root/case)
                self.assertTrue(result['geometry_checks_pass']); self.assertFalse(result['design_accepted'])
                self.assertEqual(digest(project), before)
                self.assertEqual(result['checks']['euler_characteristic'], 0)
                self.assertEqual(result['checks']['centre_bore_overlap_m3'], 0)
                self.assertEqual(result['checks']['ports'], 2)
                changed_angle = dict(data, upstream_angle_degrees=data['upstream_angle_degrees']+1)
                with self.assertRaisesRegex(ValueError, 'length and angle disagree'): inspect(root/case/'transition.ifc', changed_angle)
                if case in ('reduction', 'expansion'):
                    self.assertAlmostEqual(result['checks']['material_volume_m3'], .00152+.0076*data['transition_length_m'], places=10)
                for mutation in ('corner', 'filled', 'port', 'direction', 'source'):
                    model = ifcopenshell.open(str(root/case/'transition.ifc'))
                    fitting = model.by_type('IfcDuctFitting')[0]
                    if mutation == 'corner':
                        point = fitting.Representation.Representations[0].Items[0].FirstOperand.Outer.CfsFaces[0].Bounds[0].Bound.Polygon[0]
                        x, y, z = point.Coordinates; point.Coordinates = (x+.001, y, z)
                    elif mutation == 'filled': fitting.Representation.Representations[0].Items[0].Operator = 'UNION'
                    elif mutation == 'port':
                        port = model.by_type('IfcDistributionPort')[0]
                        matrix = placement.get_local_placement(port.ObjectPlacement); matrix[0, 3] += .001
                        api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
                    elif mutation == 'direction': model.by_type('IfcDistributionPort')[0].FlowDirection = 'NOTDEFINED'
                    else:
                        pset = next(p for p in model.by_type('IfcPropertySet') if p.Name == 'BSA_DesignInputs')
                        api.run('pset.edit_pset', model, pset=pset, properties={'Source': 'changed'})
                    bad = root/(case+'-'+mutation+'.ifc'); model.write(str(bad))
                    with self.subTest(case=case, mutation=mutation), self.assertRaises(ValueError): inspect(bad, data)

    def test_explicit_sources_and_upstream_station_disagreement(self):
        for key, value in [('source', ''), ('wall_model', 'sheet_normal'), ('section_offset_m', True), ('start_length_m', 0),
                           ('upstream_angle_degrees', 90), ('port_directions', {'start': 'SOURCE', 'end': 'SOURCE'})]:
            with self.subTest(key=key), self.assertRaises(ValueError): validate(dict(self.fixture(), **{key: value}))
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); data = self.fixture(); data['transition_length_m'] += .001
            source = root/'mismatch.json'; source.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'length differs'): run(source, root/'out')
            self.assertFalse((root/'out/transition.ifc').exists())
