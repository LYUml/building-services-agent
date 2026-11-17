import unittest
from shapely.geometry import box, mapping, shape
from bsa.service_areas import allocate_explicit
from bsa.air_allocation import prepare
from bsa.air_load import UNITS


class ExplicitServiceTests(unittest.TestCase):
    def setUp(self):
        self.boundary = box(0, 0, 10, 4).difference(box(4, 1, 5, 2))
        self.terminals = [dict(id='A', center_m=[1, 2]), dict(id='B', center_m=[8, 2])]
        self.cells = dict(B=mapping(box(6, -1, 11, 5)), A=mapping(box(-1, -1, 6, 5)))

    def test_id_binding_clipping_column_and_independent_service_boundary(self):
        result = allocate_explicit(mapping(self.boundary), self.terminals, 78, self.cells, 'Declared six-metre split')
        self.assertEqual([t['id'] for t in result['terminals']], ['A', 'B'])
        self.assertEqual([t['allocated_load_area_m2'] for t in result['terminals']], [46, 32])
        self.assertEqual(shape(result['terminals'][0]['geometry']).intersection(box(4, 1, 5, 2)).area, 0)
        self.assertFalse(result['design_accepted'])

    def test_gap_overlap_identity_and_displaced_terminal_rejected(self):
        for cells in [dict(self.cells, A=mapping(box(0, 0, 5, 4))),
                      dict(self.cells, A=mapping(box(0, 0, 7, 4))),
                      dict(self.cells, C=mapping(box(0, 0, 1, 1))),
                      dict(self.cells, A=mapping(box(2, 0, 6, 4)))]:
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                allocate_explicit(mapping(self.boundary), self.terminals, 78, cells, 'Test')
        with self.assertRaises(ValueError):
            allocate_explicit(mapping(self.boundary), self.terminals, 78, self.cells, '')

    def test_explicit_cells_drive_classified_flow_without_moving_terminal(self):
        values = dict(area=78, cooling_allowance=200, sensible_fraction=.8,
                      density=1.25, specific_heat=1000, temperature_difference=10)
        inputs = {k: dict(value=v, unit=UNITS[k], source='Synthetic test', classification='assumed') for k, v in values.items()}
        result = prepare(mapping(self.boundary), self.terminals, inputs, .4,
                         service_cells=self.cells, service_basis='Declared split')
        self.assertAlmostEqual(result['terminals'][0]['maximum_flow_L_s'], 998.4*46/78)
        self.assertAlmostEqual(result['checks']['allocated_flow_L_s'], 998.4)
        self.assertEqual(result['load']['inputs'], inputs)
        self.assertIn('explicit', result['scope'])
        with self.assertRaises(ValueError):
            prepare(mapping(self.boundary), self.terminals, inputs, .4, service_basis='Orphan basis')
