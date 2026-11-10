import copy
import json
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
import ifcopenshell.util.element as element

from tests import test_duct_fitting_chain as fixtures
from bsa import rectangular_tee_transitions as composition
from bsa import rectangular_transition as transition
from bsa import duct_fitting_span as span_tool
from bsa.duct_fitting_chain import merge, shape_hash
from bsa.duct_chain_analysis import calculate as flow_case
from bsa.duct_fitting_data import calculate, lookup, prepare
from bsa.tee_geometry import stable_guid
from bsa.cli import digest

ROOT = Path(__file__).resolve().parents[1]


class DuctFittingDataTests(unittest.TestCase):
    def test_sparse_cells_bounds_and_exact_grid_points(self):
        table = dict(axes=[dict(quantity='x', values=[1., 2.]), dict(quantity='y', values=[1., 2.])],
            coefficients=[[1., 3.], [5., 7.]])
        self.assertAlmostEqual(lookup(table, dict(x=1.5, y=1.5))['coefficient'], 4.)
        table['coefficients'][1][1] = None
        self.assertIsNone(lookup(table, dict(x=1.5, y=1.5))['coefficient'])
        self.assertEqual(lookup(table, dict(x=1., y=1.))['coefficient'], 1.)
        self.assertEqual(lookup(table, dict(x=1., y=1.5))['coefficient'], 2.)
        self.assertIn('bounds', lookup(table, dict(x=.99, y=1.))['reason'])
        constrained = copy.deepcopy(table); constrained['conditions'] = [dict(quantity='x', minimum=1., maximum=1.1)]
        self.assertIsNone(lookup(constrained, dict(x=1.5, y=1.))['coefficient'])
        self.assertFalse(lookup(constrained, dict(x=1.5, y=1.))['native_condition_checks'][0]['pass_check'])
        self.assertEqual(lookup(constrained, dict(x=1., y=1.))['coefficient'], 1.)
        self.assertIsNone(lookup(dict(axes=table['axes'], coefficients=[[1., 2.], [float('inf'), 3.]]), dict(x=1.5, y=1.5))['coefficient'])

    def test_native_reference_pressure_signed_paths_and_source_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp); paths, data, span, volume = fixtures.DuctFittingChainTests().sources(root/'sources', False)
            target = root/'chain.ifc'; merge(paths, target, data, span, volume)
            model = ifcopenshell.open(str(target)); flows = {}
            for name, amounts in [('a', {'main-a': .5, 'main-b': .3, 'branch': .2}), ('b', {'main-a': .3, 'main-b': .1, 'branch': .2})]:
                _, _, _, spec, children = composition.prepare(root/'sources'/name/'project.json')
                for arm, q in amounts.items():
                    flows[stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', arm)] = dict(flow_m3_s=q, source_section='S', source_node=name)
                    if arm in children:
                        for end in ('start', 'end'): flows[stable_guid(children[arm], 'IfcDistributionPort', transition.KEY, end)] = dict(flow_m3_s=q, source_section='S', source_node=name)
            for name in ('near', 'far'): flows[stable_guid(data, 'IfcDistributionPort', span_tool.KEY, data['section'], name)] = dict(flow_m3_s=.3, source_section='S', source_node='span')
            case = flow_case(model, flows, dict(density_kg_m3=1.2, viscosity_Pa_s=1.81e-5, roughness_m=9e-5))
            document = root/'synthetic.txt'; document.write_text('Fictional constant signed coefficients for software controls only.')
            basis = dict(sources=dict(test=dict(document='synthetic.txt', sha256=digest(document), citation='Authored mathematical fixture', edition='software test')),
                tables=[dict(source_id='test', citation_location='synthetic constant', classification='synthetic', applicability_note='Not a physical correlation',
                    friction_scope='local_dynamic_only', product_guid=r['product_guid'], geometry_sha256=shape_hash(model.by_guid(r['product_guid'])),
                    inlet_port_guid=r['inlet_port_guid'], outlet_port_guid=r['outlet_port_guid'], reference_port_guid=r['inlet_port_guid'],
                    axes=[dict(quantity='outlet_to_inlet_flow_ratio', values=[.01, 1.01])], coefficients=[-1., -1.] if i == 0 else [2., 2.])
                    for i, r in enumerate(case['missing_fitting_path_losses'])])
            path = root/'basis.json'; path.write_text(json.dumps(basis)); parsed, pins = prepare(path)
            result = calculate(model, case, parsed)
            self.assertEqual(result['calculated_table_paths'], 8); self.assertEqual(result['unsupplied_table_paths'], 0)
            for row in result['table_results']:
                obj = model.by_guid(row['product_guid']); outlet = model.by_guid(row['outlet_port_guid'])
                self.assertAlmostEqual(row['native_quantities']['deflection_deg'], 90. if obj.PredefinedType=='JUNCTION' and outlet.Name=='branch' else 0., places=9)
            constrained = copy.deepcopy(parsed)
            branch = next(r for r in constrained['tables'] if model.by_guid(r['product_guid']).PredefinedType=='JUNCTION' and model.by_guid(r['outlet_port_guid']).Name=='branch')
            branch['conditions'] = [dict(quantity='deflection_deg', minimum=0., maximum=1e-6)]
            rejected = calculate(model, case, constrained)
            self.assertEqual(rejected['calculated_table_paths'], 7)
            self.assertEqual(sum(r['status']=='native_condition_failed' for r in rejected['data_requests']), 1)
            self.assertEqual(len(result['data_requests']), 8)
            self.assertTrue(all(r['status'] == 'physical_review_required' for r in result['data_requests']))
            for request in result['data_requests']:
                self.assertEqual(request['geometry_sha256'], shape_hash(model.by_guid(request['product_guid'])))
                self.assertEqual(request['saved_design_inputs'], {k:v for k,v in element.get_psets(model.by_guid(request['product_guid']))['BSA_DesignInputs'].items() if k != 'id'})
                self.assertTrue(request['affected_outlet_port_guids'])
                self.assertTrue(all(p['owner_guid'] == request['product_guid'] for p in request['available_reference_ports']))
                expected = {p['outlet_port_guid'] for p in case['boundary_paths'] if any(
                    all(s[k] == request[k] for k in ('product_guid', 'inlet_port_guid', 'outlet_port_guid')) for s in p['steps'] if s['kind'] == 'fitting')}
                self.assertEqual(set(request['affected_outlet_port_guids']), expected)
            blank = copy.deepcopy(parsed); blank['tables'][0]['coefficients'] = [None, None]
            pending = calculate(model, case, blank)
            self.assertEqual(pending['data_requests'][0]['status'], 'table_support_missing')
            blank['tables'].pop(0); pending = calculate(model, case, blank)
            self.assertEqual(pending['data_requests'][0]['status'], 'source_data_required')
            self.assertLess(result['table_results'][0]['signed_tabulated_contribution_Pa'], 0)
            self.assertTrue(all(p['tabulated_plus_separate_straight_Pa'] is not None for p in result['boundary_paths']))
            self.assertTrue(all(p['complete_total_pressure_drop_Pa'] is None for p in result['boundary_paths']))
            self.assertFalse(result['pressure_budget_complete']); self.assertIsNone(result['critical_path']); self.assertFalse(result['design_accepted'])
            for actual, route in zip(result['boundary_paths'], case['boundary_paths']):
                expected = route['known_straight_friction_Pa']
                for step in route['steps']:
                    if step['kind'] == 'fitting':
                        row = next(r for r in basis['tables'] if all(r[k] == step[k] for k in ('product_guid', 'inlet_port_guid', 'outlet_port_guid')))
                        expected += row['coefficients'][0]*case['port_flows'][row['reference_port_guid']]['actual_velocity_pressure_Pa']
                self.assertAlmostEqual(actual['tabulated_plus_separate_straight_Pa'], expected)
            # Preserve the same physical scalar contribution when changing reference port.
            changed = copy.deepcopy(parsed); row = next(r for r in changed['tables'] if model.by_guid(r['product_guid']).PredefinedType == 'TRANSITION')
            a = case['port_flows'][row['inlet_port_guid']]['actual_velocity_pressure_Pa']; b = case['port_flows'][row['outlet_port_guid']]['actual_velocity_pressure_Pa']
            row['reference_port_guid'] = row['outlet_port_guid']; row['coefficients'] = [2*a/b]*2
            converted = calculate(model, case, changed)
            for a, b in zip(result['boundary_paths'], converted['boundary_paths']): self.assertAlmostEqual(a['tabulated_plus_separate_straight_Pa'], b['tabulated_plus_separate_straight_Pa'])
            for kind in ('geometry', 'reference', 'path'):
                bad = copy.deepcopy(parsed)
                if kind == 'geometry': bad['tables'][0]['geometry_sha256'] = '0'*64
                elif kind == 'reference': bad['tables'][0]['reference_port_guid'] = 'unknown'
                else: bad['tables'][0]['outlet_port_guid'] = 'unknown'
                with self.subTest(kind=kind), self.assertRaises(ValueError): calculate(model, case, bad)
            document.write_text('Changed source')
            with self.assertRaisesRegex(ValueError, 'hash'): prepare(path)
