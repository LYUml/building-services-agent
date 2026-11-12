import copy
import json
from pathlib import Path
import tempfile
import unittest
import uuid

import ifcopenshell
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system

from bsa.bim import run as author
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.route_join import inspect, merge

ROOT = Path(__file__).resolve().parents[1]


class RouteJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        cls.folder = Path(cls.temp.name)
        source = json.loads((ROOT/'examples/route-search/port-source-model.json').read_text())
        source['spaces'][0].update(origin_m=[-.5, -.5, 0], size_m=[5.5, 3, 3.4])
        for d, x in zip(source['devices'], [-.3, 4]):
            d.update(origin_m=[x, -.1024, 1.3976], size_m=[.3, .2048, .2048])
            d['ports'] = [dict(id=name, direction=direction, offset_m=[station, .1024, .1024], source='study')
                          for name, direction, station in [('in','SINK',0),('out','SOURCE',.3)]]
        route = copy.deepcopy(source)
        route['project_uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'bsa/route-join-test'))
        route['devices'] = [copy.deepcopy(source['devices'][0])]
        route['devices'][0].update(id='ROUTE', origin_m=[0, -.1024, 1.3976], size_m=[4, .2048, .2048])
        route['devices'][0]['ports'][1]['offset_m'][0] = 4
        for name, data in [('source', source), ('route', route)]:
            path = cls.folder/(name+'.json'); path.write_text(json.dumps(data), encoding='utf-8')
            author(path, cls.folder/name)
        cls.source = cls.folder/'source/model.ifc'; cls.route = cls.folder/'route/model.ifc'
        sf, rf = [ifcopenshell.open(str(p)) for p in (cls.source, cls.route)]
        owners = {o.Name:o for o in sf.by_type('IfcDuctSegment')}
        cls.endpoints = {}
        for role, owner_name, port_name in [('start','SUPPLY','out'),('end','RECEIVER','in')]:
            owner = owners[owner_name]; port = next(p for p in system.get_ports(owner) if p.Name==port_name)
            cls.endpoints[role] = dict(owner_guid=owner.GlobalId, port_guid=port.GlobalId)
        cls.frames = {role:dict(port_guid=next(p.GlobalId for p in rf.by_type('IfcDistributionPort') if p.Name==name))
                      for role, name in [('start','in'),('end','out')]}
        cls.joined = cls.folder/'joined.ifc'
        cls.before = {str(p):digest(p) for p in (cls.source, cls.route)}
        cls.checks, cls.expected = merge(cls.source, cls.route, cls.joined, cls.endpoints, cls.frames)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_saved_chain_preserves_sources_and_connects_every_local_body(self):
        self.assertTrue(all(v is True for k,v in self.checks.items() if k not in ('connection_count','local_chain_body_count')))
        self.assertEqual(self.checks['local_chain_body_count'], 3)
        self.assertEqual(self.checks['connection_count'], 2)
        self.assertTrue(all(digest(Path(p))==sha for p,sha in self.before.items()))
        self.assertEqual(len(ifcopenshell.open(str(self.joined)).by_type('IfcProject')), 1)

    def test_missing_link_changed_geometry_and_system_membership_reject(self):
        for fault in ('link','geometry','system','port'):
            model = ifcopenshell.open(str(self.joined))
            if fault=='link':
                model.remove(model.by_type('IfcRelConnectsPorts')[0])
            elif fault=='geometry':
                model.by_type('IfcExtrudedAreaSolid')[0].Depth += .01
            elif fault=='system':
                group=model.by_type('IfcRelAssignsToGroup')[0]
                group.RelatedObjects=group.RelatedObjects[:-1]
            else:
                port=model.by_guid(self.endpoints['start']['port_guid'])
                port.FlowDirection='SINK'
            target=self.folder/('changed-'+fault+'.ifc');model.write(str(target))
            with self.subTest(fault=fault), self.assertRaises(ProjectError):
                inspect(target,self.expected)

    def test_original_and_route_identity_overlap_rejects(self):
        with self.assertRaises(ProjectError):
            merge(self.source,self.source,self.folder/'overlap.ifc',self.endpoints,self.frames)

    def test_occupied_source_port_rejects(self):
        route=ifcopenshell.open(str(self.route));mapping={}
        for root in route.by_type('IfcRoot'):
            original=root.GlobalId;root.GlobalId=ifcopenshell.guid.new();mapping[original]=root.GlobalId
        target=self.folder/'distinct-route.ifc';route.write(str(target))
        frames={role:dict(port_guid=mapping[row['port_guid']]) for role,row in self.frames.items()}
        with self.assertRaises(ProjectError):
            merge(self.joined,target,self.folder/'occupied.ifc',self.endpoints,frames)
