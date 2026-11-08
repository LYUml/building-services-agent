import copy
import json
import math
from pathlib import Path
import unittest

from bsa.engine import ProjectError
from bsa.network_binding import prepare
from bsa.route_model import compile_route

ROOT=Path(__file__).resolve().parents[1]


class RouteModelTests(unittest.TestCase):
    def setUp(self):
        root=ROOT/'examples/route-search'
        self.route,self.settings,self.network=[json.loads((root/name).read_text()) for name in ('route-input.json','model-settings.json','network.json')]

    def test_compiled_chain_preserves_search_length_bore_and_each_loss(self):
        route,model,binding,network=compile_route(self.route,self.settings,self.network)
        derived,_=prepare(network,model,binding)
        segment=derived['segments'][0]
        self.assertAlmostEqual(segment['length_m'],route['length_m'])
        self.assertAlmostEqual(segment['minor_k'],route['bend_count']*.4)
        self.assertEqual(segment['diameter_m'],.08)
        self.assertEqual(len(model['connections']),len(model['devices'])-1)
        ports={d['id']+'.'+p['id']:[a+b for a,b in zip(d['origin_m'],p['offset_m'])] for d in model['devices'] for p in d['ports']}
        for link in model['connections']:
            self.assertLess(math.dist(ports[link['from']],ports[link['to']]),1e-8)
        self.assertLess(math.dist(ports[binding['nodes']['SOURCE']],[0,1.5,1]),1e-8)
        self.assertLess(math.dist(ports[binding['nodes']['END']],[4,1.5,1]),1e-8)

    def test_straight_route_uses_explicit_straight_loss(self):
        self.route['obstacles']=[];self.settings['straight_excess_k']=.12
        route,model,binding,network=compile_route(self.route,self.settings,self.network)
        derived,_=prepare(network,model,binding)
        self.assertEqual(len(model['devices']),1)
        self.assertEqual(derived['segments'][0]['minor_k'],.12)
        self.assertEqual(derived['segments'][0]['length_m'],4)

    def test_loss_duplication_and_uncontained_route_are_rejected(self):
        for fault in ('aggregate','room','basis','bore'):
            settings=copy.deepcopy(self.settings);network=copy.deepcopy(self.network)
            if fault=='aggregate':network['segments'][0]['minor_k']=.4
            elif fault=='room':settings['space']['size_m']=[1,1,1]
            elif fault=='basis':settings['loss_basis']='total fitting loss including friction'
            else:settings['inside_diameter_m']=.11
            with self.subTest(fault=fault),self.assertRaises(ProjectError):compile_route(self.route,settings,network)
