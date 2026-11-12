import copy
import json
from pathlib import Path
import unittest
from bsa.electrical_paths import calculate_paths, bind_facts
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class ElectricalPathTests(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'examples/electrical-paths'
        self.project=json.loads((folder/'project.json').read_text())
        self.topology=json.loads((folder/'topology.json').read_text())

    def test_shared_feeder_uses_all_downstream_loads_once(self):
        r=calculate_paths(self.project,self.topology)
        self.assertAlmostEqual(r['feeders'][0]['design_current_a'],15)
        self.assertAlmostEqual(r['feeders'][1]['design_current_a'],10)
        self.assertAlmostEqual(r['paths'][0]['total_voltage_drop_v'],4.4)
        self.assertAlmostEqual(r['paths'][1]['total_voltage_drop_v'],2.3)
        self.assertAlmostEqual(r['paths'][0]['total_voltage_drop_percent'],4.4/230*100)
        self.assertFalse(r['design_accepted'])

    def test_topology_cannot_omit_or_double_count_loads(self):
        for change in ('missing','cycle','parallel','unused','disconnected'):
            t=copy.deepcopy(self.topology)
            if change=='missing':del t['circuit_from_node']['C2']
            if change=='cycle':t['feeders'][0]['from_node']='SUB'
            if change=='parallel':t['feeders'].append(dict(t['feeders'][0],id='parallel'))
            if change=='unused':t['feeders'].append(dict(t['feeders'][0],id='unused',to_node='EMPTY'))
            if change=='disconnected':t['circuit_from_node']['C1']='UNKNOWN'
            with self.subTest(change=change),self.assertRaises(ProjectError):calculate_paths(self.project,t)

    def test_multiphase_and_invalid_coefficients_rejected(self):
        self.project['circuits'][1]['phase']='L2'
        with self.assertRaisesRegex(ProjectError,'one phase'):calculate_paths(self.project,self.topology)
        self.project['circuits'][1]['phase']='L1'
        for v in (-1,True,float('nan'),float('inf')):
            self.topology['feeders'][0]['vd_mv_a_m']=v
            with self.subTest(value=v),self.assertRaises(ProjectError):calculate_paths(self.project,self.topology)

    def test_binding_replaces_metric_without_inventing_applicability(self):
        r=calculate_paths(self.project,self.topology)
        basis=dict(facts={'normal_service':{'value':False,'source':'test'}},edition_decisions={})
        original=copy.deepcopy(basis);p=bind_facts(r,basis,'test report hash')
        self.assertEqual(basis,original)
        for circuit,item in p.items():
            self.assertFalse(item['facts']['normal_service']['value'])
            self.assertNotIn('includes_entire_installation_origin_to_equipment_path',item['facts'])
            self.assertIn(circuit,item['facts']['installation_origin_to_fixed_equipment_voltage_drop']['source'])

    def test_failed_branch_protection_survives_path_calculation(self):
        self.project['circuits'][0]['breaker_a']=1
        r=calculate_paths(self.project,self.topology)
        self.assertFalse(r['branch_calculation']['calculated_checks_pass'])
        self.assertFalse(r['branch_calculation']['circuits'][0]['checks']['ib_le_in'])

    def test_phase_separated_radials_preserve_original_loads_and_phase_currents(self):
        from bsa.engine import calculate
        p=json.loads((ROOT/'examples/water-riser/electrical.json').read_text())
        t=json.loads((ROOT/'examples/engineering-handoff/hk-electrical-topology.json').read_text())
        before=copy.deepcopy(p);result=calculate_paths(p,t)
        self.assertEqual(p,before);self.assertEqual(result['branch_calculation'],calculate(p))
        currents={r['phase']:r['design_current_a'] for r in result['feeders']}
        self.assertAlmostEqual(currents['L1'],750/.85/230)
        self.assertAlmostEqual(currents['L2'],36/.9/230)
        paths={r['circuit']:r for r in result['paths']}
        self.assertAlmostEqual(paths['PUMP-SUPPLY']['total_voltage_drop_v'],(4*20+18*12)*currents['L1']/1000)
        self.assertAlmostEqual(paths['SERVICE-LIGHTS']['total_voltage_drop_v'],(4*20+18*18)*currents['L2']/1000)
        self.assertEqual(result['phase_groups']['L1']['circuit_ids'],['PUMP-SUPPLY'])
        self.assertFalse(result['design_accepted'])

    def test_independent_groups_reject_missing_return_basis_cross_phase_nodes_and_coverage(self):
        p=json.loads((ROOT/'examples/water-riser/electrical.json').read_text())
        original=json.loads((ROOT/'examples/engineering-handoff/hk-electrical-topology.json').read_text())
        for mode in ('basis','phase','circuit','node','feeder','origin','recursive'):
            t=copy.deepcopy(original)
            if mode=='basis':t['return_path_basis']='shared neutral'
            if mode=='phase':t['radials'].pop('L2')
            if mode=='circuit':t['radials']['L1']['circuit_from_node']['SERVICE-LIGHTS']='PUMP-DB-L1'
            if mode=='node':
                t['radials']['L2']['feeders'][0]['to_node']='PUMP-DB-L1';t['radials']['L2']['circuit_from_node']['SERVICE-LIGHTS']='PUMP-DB-L1'
            if mode=='feeder':t['radials']['L2']['feeders'][0]['id']='PUMP-FEEDER'
            if mode=='origin':t['radials']['L2']['installation_origin']='SUBSTITUTE'
            if mode=='recursive':t['radials']['L2']['method']='independent_single_phase_radials'
            with self.subTest(mode=mode),self.assertRaises(ProjectError):calculate_paths(p,t)
