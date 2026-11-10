import json
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement as placement

from bsa.rectangular_tee_assembly import run, inspect, validate
from bsa.tee_geometry import stable_guid
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class RectangularTeeAssemblyTests(unittest.TestCase):
    def test_saved_material_connections_rigid_placement_and_mutations(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            assembly = json.loads((ROOT/'examples/rectangular-tee/assembly.json').read_text())
            assembly_path = root/'assembly.json'; assembly_path.write_text(json.dumps(assembly))
            for case in ('directed', 'bidirectional_rotated'):
                spec = json.loads((ROOT/'examples/rectangular-tee/project.json').read_text())
                if case == 'bidirectional_rotated':
                    spec['placement'].update(origin_m=[12, -7, 4], rotation=[[.6, 0, .8], [0, 1, 0], [-.8, 0, .6]])
                    spec['port_directions'] = {name: 'SOURCEANDSINK' for name in spec['port_directions']}
                    spec.update(internal_width_m=.5, internal_height_m=.25, wall_thickness_m=.004)
                source = root/(case+'.json'); source.write_text(json.dumps(spec)); before = digest(source)
                result = run(source, assembly_path, root/case)
                self.assertTrue(result['assembly_checks_pass']); self.assertFalse(result['design_accepted'])
                self.assertEqual(digest(source), before)
                self.assertEqual(result['checks']['ports'], 9)
                self.assertEqual(result['checks']['connections'], 3 if case == 'directed' else 6)
                self.assertEqual(result['checks']['euler_characteristic'], -2)
                self.assertEqual(result['checks']['bore_probe_overlap_m3'], [0, 0])
                for mutation in ('port_shift', 'solid_shift', 'section', 'link', 'system'):
                    model = ifcopenshell.open(str(root/case/'assembly.ifc'))
                    duct = model.by_guid(stable_guid(spec, 'IfcDuctSegment', 'RECTANGULAR-TEE', 'branch'))
                    if mutation == 'port_shift':
                        port = model.by_guid(stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', 'branch', 'near'))
                        matrix = placement.get_local_placement(port.ObjectPlacement); matrix[0, 3] += .001
                        api.run('geometry.edit_object_placement', model, product=port, matrix=matrix, is_si=True)
                    elif mutation == 'solid_shift':
                        duct.Representation.Representations[0].Items[0].Position.Location.Coordinates = (.001, 0., 0.)
                    elif mutation == 'section':
                        duct.Representation.Representations[0].Items[0].SweptArea.XDim += .001
                    elif mutation == 'link':
                        model.remove(model.by_type('IfcRelConnectsPorts')[0])
                    else:
                        model.by_type('IfcDistributionSystem')[0].IsGroupedBy[0].RelatedObjects = (duct,)
                    bad = root/(case+'-'+mutation+'.ifc'); model.write(str(bad))
                    with self.subTest(case=case, mutation=mutation), self.assertRaises(ValueError):
                        inspect(bad, spec, assembly)

    def test_requires_sourced_positive_complete_lengths(self):
        base = dict(source='Synthetic test', classification='assumed', duct_lengths_m={'main-a': .3, 'main-b': .3, 'branch': .3})
        for key, value in [('source', ''), ('classification', 'measured'), ('duct_lengths_m', {'main-a': .3}), ('duct_lengths_m', {'main-a': True, 'main-b': .3, 'branch': .3})]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate(dict(base, **{key: value}))
