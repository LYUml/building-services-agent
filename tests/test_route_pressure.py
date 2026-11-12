import copy
import json
import math
from pathlib import Path
import unittest

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.network import calculate
from bsa.route_pressure import derive,validate

ROOT=Path(__file__).resolve().parents[1]


class ExtendedRoutePressureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_route_join import RouteJoinTests
        cls.fixture=RouteJoinTests;cls.fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):cls.fixture.tearDownClass()

    def setUp(self):
        self.policy=json.loads((ROOT/'examples/route-search/extended-pressure-policy.json').read_text())
        self.original=json.loads((ROOT/'examples/route-search/vertical-air-network.json').read_text())
        self.canonical=json.loads((self.fixture.folder/'route.json').read_text())

    def derive(self,policy=None,source=None,original=None):
        return derive(source or self.fixture.joined,self.fixture.expected['local_chain_owners'],self.canonical,original or self.original,policy or self.policy)

    def test_both_source_lengths_and_outer_stations_are_used_without_changing_inputs(self):
        before=digest(self.fixture.joined);original=copy.deepcopy(self.original)
        derived,ledger=self.derive();result=calculate(derived)
        self.assertAlmostEqual(derived['segments'][0]['length_m'],4.6)
        self.assertEqual([r['name'] for r in ledger],['SUPPLY','ROUTE','RECEIVER'])
        self.assertAlmostEqual(ledger[0]['from_point_m'][0],-.3)
        self.assertAlmostEqual(ledger[-1]['to_point_m'][0],4.3)
        self.assertEqual([n['elevation_m'] for n in derived['nodes']],[1.5,1.5])
        self.assertEqual(derived['supply']['total_pressure_pa'],10)
        self.assertEqual(derived['nodes'][-1]['demand_m3_s'],.08)
        self.assertEqual(derived['nodes'][-1]['required_total_pressure_pa'],1)
        self.assertTrue(result['calculated_checks_pass'])
        partial=copy.deepcopy(derived);partial['segments'][0]['length_m']=4
        self.assertTrue(math.isclose(result['segments'][0]['friction_pa']/calculate(partial)['segments'][0]['friction_pa'],4.6/4,rel_tol=1e-12))
        self.assertEqual(self.original,original);self.assertEqual(digest(self.fixture.joined),before)

    def test_additional_interface_losses_can_fail_unchanged_pressure_target(self):
        policy=copy.deepcopy(self.policy);policy['interface_excess_k']['value']=1
        baseline,_=self.derive();derived,ledger=self.derive(policy=policy)
        self.assertTrue(calculate(baseline)['calculated_checks_pass'])
        self.assertFalse(calculate(derived)['calculated_checks_pass'])
        self.assertEqual(derived['segments'][0]['minor_k'],2)
        self.assertEqual(sum(r['downstream_interface_excess_k'] for r in ledger),2)
        self.assertEqual(derived['supply'],baseline['supply'])
        self.assertEqual(derived['nodes'],baseline['nodes'])

    def test_compiler_generated_straight_aggregate_is_counted_once(self):
        model=ifcopenshell.open(str(self.fixture.joined));obj=next(o for o in model.by_type('IfcDuctSegment') if o.Name=='ROUTE')
        pset=model.by_id(element.get_psets(obj)['BSA_DesignInputs']['id'])
        api.run('pset.edit_pset',model,pset=pset,properties={'LocalLossCoefficient':.4})
        path=self.fixture.folder/'straight-route-k.ifc';model.write(str(path))
        self.canonical['devices'][0]['properties']['LocalLossCoefficient']=.4
        original=copy.deepcopy(self.original);original['segments'][0]['minor_k']=.4
        derived,_=self.derive(source=path,original=original)
        self.assertAlmostEqual(derived['segments'][0]['minor_k'],.4)
        original['segments'][0]['minor_k']=.8
        with self.assertRaises(ProjectError):self.derive(source=path,original=original)

    def test_missing_loss_boundary_decision_or_duplicated_length_rejects(self):
        for fault in ('wall','boundary','length'):
            policy=copy.deepcopy(self.policy);original=copy.deepcopy(self.original)
            if fault=='wall':policy['source_wall_excess_k'].pop('end')
            elif fault=='boundary':policy['boundary_values']='silently_keep_old_stations'
            else:original['segments'][0]['length_m']=4
            with self.subTest(fault=fault),self.assertRaises(ProjectError):self.derive(policy=policy,original=original)

    def test_existing_native_source_loss_cannot_be_silently_replaced(self):
        model=ifcopenshell.open(str(self.fixture.joined));source=model.by_guid(self.fixture.endpoints['start']['owner_guid'])
        pset=model.by_id(element.get_psets(source)['BSA_DesignInputs']['id'])
        api.run('pset.edit_pset',model,pset=pset,properties={'LocalLossCoefficient':.5,'LocalLossBasis':'excess over centreline Darcy friction'})
        path=self.fixture.folder/'source-loss-conflict.ifc';model.write(str(path))
        with self.assertRaises(ProjectError):self.derive(source=path)

    def test_missing_native_link_or_wrong_port_direction_rejects(self):
        for fault in ('link','direction'):
            model=ifcopenshell.open(str(self.fixture.joined))
            if fault=='link':model.remove(model.by_type('IfcRelConnectsPorts')[0])
            else:model.by_guid(self.fixture.endpoints['start']['port_guid']).FlowDirection='SINK'
            path=self.fixture.folder/('pressure-'+fault+'.ifc');model.write(str(path))
            with self.subTest(fault=fault),self.assertRaises(ProjectError):self.derive(source=path)

    def test_outer_boundary_must_be_a_true_cap_and_have_no_external_peer(self):
        for fault in ('false_cap','external_peer'):
            model=ifcopenshell.open(str(self.fixture.joined));owner=model.by_guid(self.fixture.endpoints['start']['owner_guid'])
            port=next(p for p in system.get_ports(owner) if p.FlowDirection=='SINK')
            if fault=='false_cap':
                matrix=placement.get_local_placement(port.ObjectPlacement);matrix[:3,3]=[0,.3,1.5]
                api.run('geometry.edit_object_placement',model,product=port,matrix=matrix,is_si=True)
            else:
                external=api.run('root.create_entity',model,ifc_class='IfcDuctSegment',name='outside-local-subset')
                peer=api.run('system.add_port',model,element=external);peer.FlowDirection='SOURCE'
                api.run('system.connect_port',model,port1=peer,port2=port,direction='SOURCE')
            path=self.fixture.folder/('boundary-'+fault+'.ifc');model.write(str(path))
            with self.subTest(fault=fault),self.assertRaises(ProjectError):self.derive(source=path)
