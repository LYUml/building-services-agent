import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa.bim import run as author
from bsa.water_binding import run,derive
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/circulation-ifc'


class CirculationIFCTests(unittest.TestCase):
    def test_saved_geometry_circulation_and_missing_connection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);author(EX/'model.json',root/'model')
            native=root/'model/model.ifc'
            result=run(EX/'project.json',native,EX/'binding.json',root/'bound')
            self.assertTrue(result['calculated_checks_pass'])
            p=json.loads((root/'bound/network-input.json').read_text())
            self.assertEqual({r['id']:round(r['length_m'],8) for r in p['pipes']},{'REFERENCE':1,'OUTBOUND':2,'CROSS':1,'RETURN':2})
            for pipe in p['pipes']:self.assertAlmostEqual(pipe['diameter_m'],.065,places=10)
            for node in p['junctions']:self.assertAlmostEqual(node['elevation_m'],1)
            h=json.loads((root/'bound/analysis/water.json').read_text())
            self.assertTrue(h['checks']['zero_reference_exchange'])
            q=h['pumps'][0]['flow_m3_s']
            for pipe in h['pipes']:
                self.assertAlmostEqual(pipe['flow_m3_s'],0 if pipe['id']=='REFERENCE' else q,delta=1e-7)
            m=ifcopenshell.open(str(native));m.remove(m.by_type('IfcRelConnectsPorts')[0])
            broken=root/'broken.ifc';m.write(str(broken))
            with self.assertRaises(ProjectError):
                derive(broken,json.loads((EX/'project.json').read_text()),json.loads((EX/'binding.json').read_text()))
