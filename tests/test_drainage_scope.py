import unittest
from bsa.drainage_scope import separate_discharge_floors


class DrainageScopeTests(unittest.TestCase):
    def select(self, **changes):
        return separate_discharge_floors(**(dict(
            building_storeys=21, stack_scope='building',
            edition_basis='Synthetic reviewed November 2023 decision',
            works_basis='Synthetic reviewed works scope, paragraphs 3/4',
            evidence='Synthetic source survey; not real building') | changes))

    def test_height_boundaries(self):
        for n in (1, 3):
            r = self.select(building_storeys=n)
            self.assertEqual(r['status'], 'outside_supported_height_band')
            self.assertIsNone(r['separate_discharge_floor_offsets'])
        for n in (4, 20):
            r = self.select(building_storeys=n)
            self.assertEqual(r['clause'], '2(d)')
            self.assertEqual(r['separate_discharge_floor_offsets'], [0])
        self.assertEqual(self.select()['separate_discharge_floor_offsets'], [0, 1])
        self.assertFalse(self.select()['design_accepted'])

    def test_special_scope_not_building_or_served_count(self):
        r = self.select(stack_scope='podium_only', scope_storeys=4)
        self.assertEqual(r['clause'], '2(d)')
        self.assertEqual(r['effective_storeys'], 4)
        self.assertEqual(self.select(stack_scope='basement_only')['status'], 'pending')
        self.assertEqual(self.select(stack_scope='basement_only', scope_storeys=2)['status'],
                         'outside_supported_height_band')
        with self.assertRaises(ValueError):
            self.select(scope_storeys=10)

    def test_unknowns_do_not_select_or_accept(self):
        for changes in [dict(building_storeys=None), dict(stack_scope=None),
                        dict(edition_basis=''), dict(works_basis=None), dict(evidence='')]:
            r = self.select(**changes)
            self.assertEqual(r['status'], 'pending')
            self.assertIsNone(r['separate_discharge_floor_offsets'])
            self.assertFalse(r['design_accepted'])

    def test_invalid_counts_and_scope(self):
        for changes in [dict(building_storeys=True), dict(building_storeys=0),
                        dict(building_storeys=20.1), dict(scope_storeys=-1),
                        dict(stack_scope='served_floors')]:
            with self.assertRaises(ValueError):
                self.select(**changes)
