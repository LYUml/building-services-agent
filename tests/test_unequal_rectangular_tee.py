import json
from pathlib import Path
import tempfile
import unittest

import ifcopenshell

from bsa.unequal_rectangular_tee import run, verify, inspect, validate

ROOT = Path(__file__).resolve().parents[1]


class UnequalTeeTests(unittest.TestCase):
    def data(self):
        return dict(tee=json.loads((ROOT/'examples/rectangular-tee/project.json').read_text()), branch_section_m=[.2, .15])

    def test_native_reduced_branch_rotated_and_corruption(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as directory:
            root = Path(directory)
            for name, height in [('reduced-height', .15), ('same-height', .2)]:
                data = self.data(); data['branch_section_m'][1] = height
                data['tee']['placement'].update(origin_m=[12, -7, 4], rotation=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
                source = root/(name+'.json'); source.write_text(json.dumps(data))
                result = run(source, root/name)
                self.assertEqual(result['checks']['euler_characteristic'], -2)
                self.assertTrue(verify(root/name)['integrity_pass'])
                receipt = root/name/'result.json'; record = json.loads(receipt.read_text()); record['design_accepted'] = True; receipt.write_text(json.dumps(record))
                with self.assertRaises(ValueError):
                    verify(root/name)
                record['design_accepted'] = False; receipt.write_text(json.dumps(record))
                path = root/name/'unequal-tee.ifc'; model = ifcopenshell.open(str(path))
                fitting = model.by_type('IfcDuctFitting')[0]
                fitting.Representation.Representations[0].Items[0].FirstOperand.SecondOperand.SweptArea.XDim += .01
                bad = root/(name+'-bad.ifc'); model.write(str(bad))
                with self.assertRaises(ValueError):
                    inspect(bad, data)
                record = json.loads(receipt.read_text()); record['inputs'] = {str(source): record['inputs'][str(source)]}; receipt.write_text(json.dumps(record))
                with self.assertRaises(ValueError):
                    verify(root/name)

    def test_invalid_or_unclassified_sections(self):
        for section in ([.4, .2], [.41, .15], [.2, .21], [True, .1], [float('nan'), .1], [0, .1]):
            data = self.data(); data['branch_section_m'] = section
            with self.assertRaises(ValueError):
                validate(data)
        data = self.data(); data['tee']['classification'] = 'measured'
        with self.assertRaises(ValueError):
            validate(data)


if __name__ == '__main__':
    unittest.main()
