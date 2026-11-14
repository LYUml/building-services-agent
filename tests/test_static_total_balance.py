import unittest
from bsa.static_total_balance import calculate


class PressureStationBalance(unittest.TestCase):
    def at(self, ps, ai, ao):
        return calculate(ps, .4, 1.2, ai, ao, station_basis='Declared test stations')

    def test_intermediate_station_cancels_in_series(self):
        ab = self.at(11., .05, .12)
        bc = self.at(7., .12, .08)
        ac = self.at(18., .05, .08)
        self.assertAlmostEqual(ab['conditional_total_difference_Pa'] +
                               bc['conditional_total_difference_Pa'],
                               ac['conditional_total_difference_Pa'])

    def test_equal_area_and_static_regain_are_distinct(self):
        self.assertEqual(self.at(11., .05, .05)['conditional_total_difference_Pa'], 11.)
        r = self.at(-10., .05, .12)
        self.assertGreater(r['conditional_total_difference_Pa'], 0)
        self.assertLess(r['static_difference_Pa'], 0)
        self.assertIsNone(r['actual_controlled_device_loss_Pa'])

    def test_incompatible_passive_case_is_not_clamped(self):
        r = self.at(1., .12, .05)
        self.assertLess(r['conditional_total_difference_Pa'], 0)
        self.assertFalse(r['passive_loss_sign_consistent'])
        self.assertFalse(r['design_accepted'])

    def test_unknown_zero_boolean_and_unlabelled_stations_reject(self):
        for value in (None, 0., True):
            with self.subTest(area=value), self.assertRaises(ValueError):
                self.at(1., value, .05)
        with self.assertRaises(ValueError):
            calculate(1., .4, 1.2, .05, .12, station_basis='')
