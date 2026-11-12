import json
import unittest
from pathlib import Path
import ifcopenshell
from bsa.spatial_terminal_ifc import run,verify
from bsa.cli import digest
from tests import test_spatial_terminal_performance as fixtures

class SpatialTerminalIFCTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.SpatialTerminalPerformanceTests();f.setUp();self.addCleanup(f.temp.cleanup);self.f=f;out,_=f.run_workflow();self.source=out/'terminal-performance/terminal-performance.json'
        report=json.loads(self.source.read_text());self.basis=f.root/'envelope-basis.json'
        self.rows={name:dict(size_m=dict(value=[.1,.1,.1],unit='m',source='Explicit synthetic envelope dimensions',classification='design_choice'),bottom_above_floor_m=dict(value=2.7,unit='m',source='Synthetic elevation assumption',classification='assumed')) for name in report['calculation']['terminals']}
        self.basis.write_text(json.dumps(self.rows))

    def test_saved_envelopes_original_entity_preservation_and_tampering(self):
        folder=self.f.root/'terminal-ifc';result=run(self.source,self.basis,folder);self.assertEqual(len(verify(folder)['terminals']),3);self.assertFalse(result['design_accepted'])
        target=folder/'Terminal Envelope Study.ifc';model=ifcopenshell.open(str(target));obj=next(o for o in model.by_type('IfcAirTerminal') if (o.Tag or '').startswith('BSA_SPATIAL:'));obj.ObjectPlacement.RelativePlacement.Location.Coordinates=(999.,999.,999.);model.write(str(target))
        record=folder/'terminal-ifc.json';report=json.loads(record.read_text());report['ifc_sha256']=digest(target);record.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'geometry differs'):verify(folder)

    def test_invalid_elevation_and_incomplete_basis_reject_before_output(self):
        for kind in ('elevation','coverage','source'):
            rows=json.loads(json.dumps(self.rows))
            if kind=='elevation':next(iter(rows.values()))['bottom_above_floor_m']['value']=3
            elif kind=='coverage':rows.pop(next(iter(rows)))
            else:next(iter(rows.values()))['size_m']['source']=''
            self.basis.write_text(json.dumps(rows));out=self.f.root/('rejected-'+kind)
            with self.subTest(kind=kind),self.assertRaises(ValueError):run(self.source,self.basis,out)
            self.assertFalse(out.exists())

