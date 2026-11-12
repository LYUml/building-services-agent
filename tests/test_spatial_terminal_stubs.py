import copy
import json
import unittest
import ifcopenshell
from bsa.cli import digest
from bsa.spatial_terminal_inlets import run as inlet_author
from bsa.spatial_terminal_stubs import run,verify
from tests import test_spatial_terminal_inlets as fixtures

class SpatialTerminalStubTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.SpatialTerminalInletTests();fixture.setUp();self.addCleanup(fixture.doCleanups);self.root=fixture.f.f.root
        self.source=self.root/'stub-inlets';r=inlet_author(fixture.source/'terminal-ifc.json',fixture.basis,self.source)
        self.rows={row['terminal']:dict(length_m=dict(value=.1,unit='m',source='Synthetic short branch',classification='design_choice'),internal_diameter_m=dict(value=row['diameter_m'],unit='m',source='Synthetic bore equals nominal assumption',classification='assumed'),wall_thickness_m=dict(value=.0005,unit='m',source='Synthetic wall choice',classification='design_choice')) for row in r['inlets']}
        self.basis=self.root/'stub-basis.json';self.basis.write_text(json.dumps(self.rows))

    def test_saved_hollow_geometry_directed_links_and_missing_link_rejected(self):
        out=self.root/'stubs';r=run(self.source/'terminal-inlets.json',self.basis,out);self.assertEqual(len(verify(out)['stubs']),3);self.assertTrue(r['original_entities_unchanged']);self.assertFalse(r['network_continuity_verified']);self.assertFalse(r['design_accepted'])
        target=out/'Terminal Stub Study.ifc';original_bytes=target.read_bytes();model=ifcopenshell.open(str(target));stub=model.by_guid(r['stubs'][0]['stub_guid']);solid=stub.Representation.Representations[0].Items[0];solid.Position.Location.Coordinates=(0.,0.,.02);model.write(str(target));r['ifc_sha256']=digest(target);(out/'terminal-stubs.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'bounds differ'):verify(out)
        target.write_bytes(original_bytes);r['ifc_sha256']=digest(target);(out/'terminal-stubs.json').write_text(json.dumps(r))
        model=ifcopenshell.open(str(out/'Terminal Stub Study.ifc'));added={row['inlet_guid'] for row in r['stubs']};links=[rel for rel in model.by_type('IfcRelConnectsPorts') if rel.RelatedPort.GlobalId in added];self.assertEqual(len(links),3)
        model.remove(links[0]);target=out/'Terminal Stub Study.ifc';model.write(str(target));r['ifc_sha256']=digest(target);(out/'terminal-stubs.json').write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'links differ'):verify(out)

    def test_invalid_length_bore_wall_and_source_reject_before_output(self):
        for kind in ('length','bore','wall','source'):
            rows=copy.deepcopy(self.rows);row=next(iter(rows.values()))
            if kind=='length':row['length_m']['value']=0
            elif kind=='bore':row['internal_diameter_m']['value']*=2
            elif kind=='wall':row['wall_thickness_m']['value']=-.1
            else:row['length_m']['source']=''
            self.basis.write_text(json.dumps(rows));out=self.root/('rejected-'+kind)
            with self.subTest(kind=kind),self.assertRaises(ValueError):run(self.source/'terminal-inlets.json',self.basis,out)
            self.assertFalse(out.exists())
