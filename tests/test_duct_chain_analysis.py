import copy
import math
from pathlib import Path
import tempfile
import unittest

import ifcopenshell

from tests import test_duct_fitting_chain as fixtures
from bsa import rectangular_tee_transitions as composition
from bsa import rectangular_transition as transition
from bsa import duct_fitting_span as span_tool
from bsa.duct_fitting_chain import merge
from bsa.duct_chain_analysis import calculate
from bsa.tee_geometry import stable_guid

ROOT = Path(__file__).resolve().parents[1]


class DuctChainAnalysisTests(unittest.TestCase):
    def test_native_port_flows_straight_friction_and_missing_fittings(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root = Path(tmp)
            paths, data, span, volume = fixtures.DuctFittingChainTests().sources(root/'sources', False)
            target = root/'chain.ifc'; merge(paths, target, data, span, volume)
            model = ifcopenshell.open(str(target)); flows = {}
            for name, amounts in [('a', {'main-a': .5, 'main-b': .3, 'branch': .2}), ('b', {'main-a': .3, 'main-b': .1, 'branch': .2})]:
                _, _, _, spec, children = composition.prepare(root/'sources'/name/'project.json')
                for arm, q in amounts.items():
                    flows[stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', arm)] = dict(flow_m3_s=q, source_section='S', source_node=name)
                    if arm in children:
                        for end in ('start', 'end'): flows[stable_guid(children[arm], 'IfcDistributionPort', transition.KEY, end)] = dict(flow_m3_s=q, source_section='S', source_node=name)
            span_ports = [stable_guid(data, 'IfcDistributionPort', span_tool.KEY, data['section'], name) for name in ('near', 'far')]
            for g in span_ports: flows[g] = dict(flow_m3_s=.3, source_section='S', source_node='span')
            air = dict(density_kg_m3=1.2, viscosity_Pa_s=1.81e-5, roughness_m=9e-5)
            result = calculate(model, flows, air)
            self.assertTrue(result['flow_continuity_pass']); self.assertEqual(len(result['port_flows']), 16)
            self.assertEqual(len(result['products']), 7); self.assertEqual(len(result['interfaces']), 6)
            self.assertEqual(len(result['boundary_ports']), 4); self.assertAlmostEqual(result['boundary_inlet_flow_m3_s'], .5)
            self.assertAlmostEqual(result['boundary_outlet_flow_m3_s'], .5)
            self.assertEqual(len(result['missing_fitting_path_losses']), 8)
            self.assertTrue(all(r['coefficient'] is None for r in result['missing_fitting_path_losses']))
            self.assertIsNone(result['complete_chain_pressure_drop_Pa']); self.assertFalse(result['pressure_budget_complete']); self.assertFalse(result['design_accepted'])
            self.assertEqual(result['status'], 'pending')
            row = result['straight_sections'][0]; calc = row['calculation']; de = calc['equivalent_diameter_m']; f = calc['darcy_factor']; re = calc['reynolds']
            independent_length = 4-.7-.2-.2/(2*math.tan(math.radians(15)))-.5
            self.assertAlmostEqual(row['length_m'], independent_length, places=10)
            self.assertAlmostEqual(calc['actual_velocity_m_s'], .3/(.4*.2), places=12)
            self.assertNotAlmostEqual(calc['actual_velocity_m_s'], calc['equivalent_round_velocity_m_s'], places=4)
            self.assertAlmostEqual(1/math.sqrt(f)+2*math.log10(air['roughness_m']/(3.7*de)+2.51/(re*math.sqrt(f))), 0, places=8)
            independent_loss = f*independent_length/de*air['density_kg_m3']*(4*.3/(math.pi*de**2))**2/2
            self.assertAlmostEqual(row['straight_friction_Pa'], independent_loss, places=10)
            self.assertAlmostEqual(result['port_flows'][span_ports[0]]['actual_velocity_pressure_Pa'], 1.2*(.3/(.4*.2))**2/2, places=12)
            for case in ('product', 'interface', 'missing', 'negative', 'air'):
                altered = copy.deepcopy(flows); properties = dict(air)
                if case == 'product': altered[next(iter(altered))]['flow_m3_s'] += .01
                elif case == 'interface':
                    for g in span_ports: altered[g]['flow_m3_s'] += .01
                elif case == 'missing': altered.pop(next(iter(altered)))
                elif case == 'negative': altered[next(iter(altered))]['flow_m3_s'] = -1
                else: properties['viscosity_Pa_s'] = True
                with self.subTest(case=case), self.assertRaises(ValueError): calculate(model, altered, properties)

    def test_empty_model_cannot_pass_flow_conservation(self):
        model = ifcopenshell.file(schema='IFC4')
        with self.assertRaisesRegex(ValueError, 'nonempty'): calculate(model, {}, dict(density_kg_m3=1.2, viscosity_Pa_s=1.81e-5, roughness_m=9e-5))
