import copy
import tempfile
import unittest
from pathlib import Path
import ezdxf
from bsa.vav_schedule import rows_from, author, cells
from bsa.duct_sheet_native import compare


class VAVScheduleTests(unittest.TestCase):
    def setUp(self):
        self.allocation = dict(terminals=[
            dict(id='SD-01', maximum_flow_L_s=100, minimum_flow_L_s=40),
            dict(id='SD-02', maximum_flow_L_s=150, minimum_flow_L_s=60)])
        self.review = dict(groups=[dict(id='VAV-01', outlet_count=2, maximum_flow_L_s=250,
            routes=[dict(terminal='SD-01', plan_length_m=2.5), dict(terminal='SD-02', plan_length_m=3.25)])])

    def test_independent_group_flow_and_lengths(self):
        row = rows_from(self.review, self.allocation)[0]
        self.assertEqual((row['maximum_flow_L_s'], row['minimum_flow_L_s']), (250, 100))
        self.assertEqual((row['minimum_plan_length_m'], row['maximum_plan_length_m']), (2.5, 3.25))
        self.assertEqual(cells(row), ['VAV-01', 'SD-01, SD-02', '250.0', '100.0', '2.500', '3.250', '2'])

    def test_missing_duplicate_and_extra_membership_rejected(self):
        for terminal in ('SD-01', 'missing'):
            r = copy.deepcopy(self.review); r['groups'][0]['routes'][1]['terminal'] = terminal
            with self.assertRaisesRegex(ValueError, 'membership'): rows_from(r, self.allocation)
        self.allocation['terminals'].append(dict(id='extra', maximum_flow_L_s=1, minimum_flow_L_s=.4))
        with self.assertRaisesRegex(ValueError, 'coverage'): rows_from(self.review, self.allocation)

    def test_duplicate_terminal_and_vav_identity_rejected(self):
        a = copy.deepcopy(self.allocation); a['terminals'].append(a['terminals'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate terminal'): rows_from(self.review, a)
        self.review['groups'].append(self.review['groups'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate VAV'): rows_from(self.review, self.allocation)

    def test_nonfinite_boolean_negative_and_wrong_flows_rejected(self):
        for bad in (True, float('nan'), -1, 0, 200):
            a = copy.deepcopy(self.allocation); a['terminals'][0]['minimum_flow_L_s'] = bad
            with self.assertRaises(ValueError): rows_from(self.review, a)
        self.review['groups'][0]['maximum_flow_L_s'] = 251
        with self.assertRaisesRegex(ValueError, 'differs'): rows_from(self.review, self.allocation)

    def test_invalid_route_lengths_rejected(self):
        for bad in (True, float('inf'), 0, -1):
            r = copy.deepcopy(self.review); r['groups'][0]['routes'][0]['plan_length_m'] = bad
            with self.assertRaisesRegex(ValueError, 'length'): rows_from(r, self.allocation)

    def test_saved_native_table_mutation_detected(self):
        rows = rows_from(self.review, self.allocation)
        with tempfile.TemporaryDirectory() as temp:
            a, b = (Path(temp)/name for name in ('a.dxf', 'b.dxf'))
            author(rows, a); author(rows, b)
            self.assertTrue(compare(a, b, ['BSA_VAV_TABLE'])['generated_native_correspondence'])
            doc = ezdxf.readfile(b)
            text = next(e for e in doc.modelspace().query('TEXT') if e.dxf.text == '250.0')
            text.dxf.text = '251.0'; doc.saveas(b)
            with self.assertRaisesRegex(ValueError, 'attributes'): compare(a, b, ['BSA_VAV_TABLE'])

    def test_long_label_refuses_silent_clipping(self):
        rows = rows_from(self.review, self.allocation); rows[0]['id'] = 'long'*30
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'exceeds'): author(rows, Path(temp)/'table.dxf')


if __name__ == '__main__': unittest.main()
