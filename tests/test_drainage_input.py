import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.drainage_input import compile_input, run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/drainage-preparation/project.json'


class DrainagePreparationTests(unittest.TestCase):
    def test_si_units_offsets_and_no_simulation_claim(self):
        data=json.loads(EXAMPLE.read_text());data['conduits'][0]['inlet_offset_m']=0.1
        text,geometry=compile_input(data)
        self.assertIn('FLOW_UNITS LPS',text)
        self.assertIn('LINK_OFFSETS DEPTH',text)
        self.assertIn('C1 J1 J2 20 0.013 0.1 0 0 0',text)
        self.assertIn('C1 CIRCULAR 0.15 0 0 0 1',text)
        self.assertAlmostEqual(geometry[0]['slope'],0.015)
        with tempfile.TemporaryDirectory() as folder:
            result=run(EXAMPLE,Path(folder)/'out')
            self.assertFalse(result['native_parse_verified'])
            self.assertFalse(result['simulation_executed'])
            self.assertFalse(result['design_accepted'])

    def test_bad_sources_geometry_and_injection_rejected(self):
        original=json.loads(EXAMPLE.read_text())
        mutations=[lambda d:d['conduits'][0].update(source='missing'),
                   lambda d:d['conduits'][0].update(length_m=True),
                   lambda d:d['conduits'][0].update(manning_n=float('nan')),
                   lambda d:d['conduits'][0].update(outlet_offset_m=1),
                   lambda d:d['conduits'][0].update(id='C1\n[FILES]'),
                   lambda d:d['conduits'][1].update(id='c1'),
                   lambda d:d['conduits'][1].update(to='missing'),
                   lambda d:d['conduits'].pop(),
                   lambda d:d.update(rainfall='silently ignored?')]
        for mutate in mutations:
            d=copy.deepcopy(original);mutate(d)
            with self.assertRaises(ProjectError):compile_input(d)


if __name__=='__main__':unittest.main()
