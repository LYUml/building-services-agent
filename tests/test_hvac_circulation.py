import copy
import json
from pathlib import Path
import tempfile
import unittest
from bsa.engine import ProjectError
from bsa.epanet import validate,run,MODEL

ROOT=Path(__file__).resolve().parents[1]


class CirculationTests(unittest.TestCase):
    def test_explicit_mode_and_return_path_required(self):
        source=json.loads((ROOT/'examples/hvac-circulation/project.json').read_text())
        for change in ('ordinary','withdrawal','no-pump','no-return','pda'):
            p=copy.deepcopy(source)
            if change=='ordinary':p['model']=MODEL
            elif change=='withdrawal':p['junctions'][0]['demand_m3_s']=.001
            elif change=='no-pump':p['pumps']=[]
            elif change=='no-return':p['pipes']=[r for r in p['pipes'] if r['id']!='RETURN-PIPE']
            else:p['hydraulics']['demand_model']='PDA'
            with self.subTest(change=change),self.assertRaises(ProjectError):validate(p)

    def test_actual_circulation_is_independent_of_reference_head_offset(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);source=ROOT/'examples/hvac-circulation/project.json'
            a=run(source,root/'base')
            p=json.loads(source.read_text());p['reservoirs'][0]['head_m']+=10
            changed=root/'raised.json';changed.write_text(json.dumps(p));b=run(changed,root/'raised')
            for r in (a,b):
                self.assertTrue(r['calculated_checks_pass'],r.get('checks'))
                self.assertAlmostEqual(r['reservoir_demands_m3_s']['REF'],0,delta=1e-7)
                self.assertGreater(r['pumps'][0]['flow_m3_s'],0)
                self.assertIsNone(r['pumps'][0]['electrical_power_kw'])
                flows={s['id']:s['flow_m3_s'] for s in r['pipes']}
                self.assertAlmostEqual(flows['OUTBOUND'],flows['RETURN-PIPE'],delta=1e-7)
            self.assertAlmostEqual(a['pumps'][0]['flow_m3_s'],b['pumps'][0]['flow_m3_s'],delta=1e-7)
            for first,second in zip(a['junctions'],b['junctions']):
                self.assertAlmostEqual(second['static_pressure_head_m']-first['static_pressure_head_m'],10,delta=1e-4)


if __name__=='__main__':unittest.main()
