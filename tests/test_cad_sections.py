import copy
import unittest
import ezdxf
from bsa.cad_sections import measure, validate
from bsa.engine import ProjectError


class SectionTests(unittest.TestCase):
    def fixture(self):
        doc = ezdxf.new('R2018'); doc.units = 1
        doc.layers.new('BSA_SECTION_port')
        row = {'id': 'port', 'source': 'Synthetic section', 'plane': 'YZ',
               'centre_drawing_units': [2.7, 0, 0]}
        for radius in (.5, 1):
            doc.modelspace().add_circle((0, 0, 2.7), radius,
                dxfattribs={'extrusion': (1, 0, 0), 'layer': 'BSA_SECTION_port'})
        return doc, row

    def test_world_coordinates_and_inch_conversion(self):
        doc, row = self.fixture(); result = measure(doc, row, 1, 1e-8)
        self.assertAlmostEqual(result['inner_diameter_m'], .0254)
        self.assertAlmostEqual(result['outer_diameter_m'], .0508)
        self.assertEqual(result['centre_m'], [.06858, 0, 0])

    def test_filled_disc_extra_boundary_and_wrong_plane_reject(self):
        doc, row = self.fixture(); doc.modelspace().delete_entity(list(doc.modelspace())[0])
        with self.assertRaises(ProjectError): measure(doc, row, 1, 1e-8)
        doc, row = self.fixture()
        doc.modelspace().add_circle((0, 0), 2, dxfattribs={'layer': 'BSA_SECTION_port'})
        with self.assertRaises(ProjectError): measure(doc, row, 1, 1e-8)
        doc, row = self.fixture(); row['plane'] = 'XY'
        with self.assertRaises(ProjectError): measure(doc, row, 1, 1e-8)

    def test_nonconcentric_wrong_units_and_shifted_location_reject(self):
        doc, row = self.fixture(); list(doc.modelspace())[0].dxf.center = (.1, 0, 2.7)
        with self.assertRaises(ProjectError): measure(doc, row, 1, 1e-8)
        doc, row = self.fixture()
        with self.assertRaises(ProjectError): measure(doc, row, 4, 1e-8)
        row['centre_drawing_units'][0] += .1
        with self.assertRaises(ProjectError): measure(doc, row, 1, 1e-8)

    def test_invalid_or_ambiguous_basis_reject(self):
        row = self.fixture()[1]
        basis = {'source': 'Synthetic control', 'drawing_sha256': 'a'*64, 'solid_handle': '94',
                 'insunits': 1, 'tolerance_m': 1e-8, 'sections': [row]}
        validate(basis)
        for update in ({'tolerance_m': float('nan')}, {'tolerance_m': 0}, {'insunits': True},
                       {'sections': []}, {'sections': [row, row]}, {'solid_handle': 'not a handle'}):
            with self.subTest(update=update), self.assertRaises(ProjectError):
                validate(dict(basis, **update))
        bad = copy.deepcopy(basis); bad['sections'][0]['id'] = '../outside'
        with self.assertRaises(ProjectError): validate(bad)
