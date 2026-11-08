import copy
import json
from pathlib import Path
import unittest
from bsa.engine import ProjectError
from bsa.network_binding import prepare

ROOT=Path(__file__).resolve().parents[1]/'examples/regulations-hk-water-branches'


class FaceJunctionTests(unittest.TestCase):
    def test_explicit_face_mode_derives_lengths_and_rejects_implicit_mode(self):
        n,m,b=[json.loads((ROOT/(name+'.json')).read_text()) for name in ('skeleton','face-model','face-binding')]
        result,_=prepare(n,m,b)
        lengths={s['id']:s['length_m'] for s in result['segments']}
        for key,value in {'TRUNK':7.9,'BRANCH-A':5.9,'BRANCH-B':8.9}.items():self.assertAlmostEqual(lengths[key],value)
        legacy=copy.deepcopy(b);del legacy['node_port_mode']
        with self.assertRaisesRegex(ProjectError,'endpoints differ'):prepare(n,m,legacy)
        broken=copy.deepcopy(m);broken['connections']=[c for c in broken['connections'] if c['from']!='JUNCTION.a']
        with self.assertRaises(ProjectError):prepare(n,broken,b)
        shifted=copy.deepcopy(m)
        junction=next(d for d in shifted['devices'] if d['id']=='JUNCTION')
        junction['ports'][0]['offset_m'][2]+=.01
        with self.assertRaises(ProjectError):prepare(n,shifted,b)


if __name__=='__main__':unittest.main()
