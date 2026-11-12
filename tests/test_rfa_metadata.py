import unittest
from bsa.rfa_metadata import partatom

XML=b'''<entry xmlns="http://www.w3.org/2005/Atom" xmlns:A="urn:schemas-autodesk-com:partatom"><title>Synthetic parser control</title><A:family><A:variationCount>1</A:variationCount><A:part><title>Example</title><Radius units="in" typeOfParameter="Length">6"</Radius><Flow units="CFM">0 CFM</Flow></A:part></A:family></entry>'''

class RfaMetadataTests(unittest.TestCase):
    def test_preserves_raw_dimension_semantics_and_unassigned_flow(self):
        r=partatom(XML);p=r['types'][0]['parameters'];self.assertEqual(p[0]['name'],'Radius');self.assertEqual(p[0]['raw_value'],'6"');self.assertEqual(p[0]['attributes']['units'],'in');self.assertEqual(p[1]['raw_value'],'0 CFM')
    def test_unsupported_or_ambiguous_structure_rejects(self):
        for data in [XML.replace(b'<A:variationCount>1',b'<A:variationCount>2'),XML.replace(b'<Flow units="CFM">0 CFM</Flow>',b'<Radius>2</Radius>'),XML.replace(b'<title>Example</title>',b'<title/>'),XML.replace(b'<Radius units="in" typeOfParameter="Length">6"</Radius>',b'<Radius><child/></Radius>')]:
            with self.subTest(data=data),self.assertRaises(ValueError):partatom(data)
    def test_dtd_entities_and_oversized_input_reject(self):
        for data in [b'<!DOCTYPE entry>'+XML,b'<!ENTITY x "value">'+XML,b' '*(2*1024*1024+1)]:
            with self.assertRaises(ValueError):partatom(data)
