"""Pure geometry interface controls; these do not require MOOSAS or a solver."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from moosas_space_exchange import space_contacts
from bsa.engine import ProjectError


class MoosasContactTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(id='A',source='synthetic',origin_m=[0,0,0],size_m=[4,3,2]),
                     dict(id='B',source='synthetic',origin_m=[4,0,0],size_m=[5,3,2])]
        self.binding = {'spaces':[{'id':'A','guid':'guid-a'},{'id':'B','guid':'guid-b'}]}

    def test_horizontal_pair_and_reversed_input(self):
        row = space_contacts(self.rows,self.binding)[0]
        self.assertEqual(row,dict(spaces=['guid-a','guid-b'],axis=0,area_m2=6,
                                  surfaces=['guid-a_3','guid-b_5']))
        reverse = space_contacts(list(reversed(self.rows)),self.binding)[0]
        self.assertEqual(reverse['surfaces'],['guid-b_5','guid-a_3'])

    def test_stacked_ceiling_floor(self):
        self.rows[1].update(origin_m=[0,0,2],size_m=[4,3,5])
        row = space_contacts(self.rows,self.binding)[0]
        self.assertEqual(row['surfaces'],['guid-a_1','guid-b_0'])
        self.assertEqual(row['area_m2'],12)

    def test_overlap_and_partial_contact_rejected(self):
        for origin in ([3,0,0],[4,1,0]):
            rows=copy.deepcopy(self.rows);rows[1]['origin_m']=origin
            with self.subTest(origin=origin),self.assertRaises(ProjectError):
                space_contacts(rows,self.binding)

    def test_separated_and_edge_contact_not_interfaces(self):
        for origin in ([5,0,0],[4,3,0]):
            rows=copy.deepcopy(self.rows);rows[1]['origin_m']=origin
            self.assertEqual(space_contacts(rows,self.binding),[])


if __name__=='__main__': unittest.main()
