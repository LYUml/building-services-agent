import copy
import unittest
from bsa.drainage_connections import review


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.scope = dict(building_storeys=21, stack_scope='building',
                          edition_basis='Synthetic reviewed edition', works_basis='Synthetic works review',
                          evidence='Synthetic survey floor counts')
        self.rows = [dict(id='WC-0', floor_offset=0, connected_to_stack=False,
                          separate_to_manhole=True, source='Synthetic surveyed connection'),
                     dict(id='WC-1', floor_offset=1, connected_to_stack=False,
                          separate_to_manhole=True, source='Synthetic surveyed connection')]

    def call(self, rows=None, **changes):
        return review(self.scope, self.rows if rows is None else rows,
                      **(dict(inventory_complete=True, inventory_source='Synthetic complete survey') | changes))

    def test_upper_floor_is_restricted_only_above_twenty(self):
        self.rows[1]['connected_to_stack'] = True
        self.assertEqual(self.call()['status'], 'fail')
        self.scope['building_storeys'] = 20
        self.assertEqual(self.call()['status'], 'pass')
        self.assertEqual(self.call()['fixtures'][1]['status'], 'outside_selected_floors')

    def test_both_no_stack_and_direct_manhole_required(self):
        self.assertEqual(self.call()['status'], 'pass')
        self.rows[0]['separate_to_manhole'] = False
        self.assertEqual(self.call()['status'], 'fail')
        self.rows[0]['separate_to_manhole'] = None
        self.assertEqual(self.call()['status'], 'pending')
        self.rows[0]['connected_to_stack'] = True
        self.assertEqual(self.call(inventory_complete=None)['status'], 'fail')

    def test_empty_and_incomplete_inventory(self):
        self.assertEqual(self.call([])['status'], 'pass')
        self.assertEqual(self.call([], inventory_complete=None)['status'], 'pending')
        self.assertEqual(self.call(inventory_complete=False)['status'], 'pending')
        self.assertFalse(self.call()['design_accepted'])

    def test_unknown_floor_scope_and_invalid_inventory(self):
        self.rows[1]['floor_offset'] = None
        self.assertEqual(self.call()['status'], 'pending')
        self.scope['works_basis'] = None
        self.assertEqual(self.call()['status'], 'pending')
        for change in [dict(floor_offset=True), dict(connected_to_stack=1), dict(source='')]:
            rows = copy.deepcopy(self.rows)
            rows[0].update(change)
            with self.assertRaises(ValueError): self.call(rows)
        with self.assertRaises(ValueError): self.call(self.rows + self.rows)
