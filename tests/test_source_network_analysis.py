import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ifcopenshell
import ifcopenshell.util.system as system
from bsa import source_network_analysis as tool,rectangular_tee
from tests import test_rectangular_cross as fixtures


class SourceNetworkAnalysisTests(unittest.TestCase):
    def graph(self):
        owned=dict(A=['ai','ab','ac'],B=['bi','bo'],C=['ci','co']);directions={p:'SINK' if p in ('ai','bi','ci') else 'SOURCE' for ports in owned.values() for p in ports};expected={p:dict(flow_m3_s=q) for p,q in [('ai',3.),('ab',1.),('ac',2.),('bi',1.),('bo',1.),('ci',2.),('co',2.)]}
        return owned,directions,[('ab','bi'),('ac','ci')],expected

    def test_actual_downstream_demands_reconcile_every_source_port(self):
        args=self.graph();actual=tool.prescribed_flows(*args);self.assertEqual(actual['ai'],3);self.assertEqual(actual['bi'],1);self.assertEqual(actual['ci'],2)
        args[3]['ai']['flow_m3_s']=4
        with self.assertRaisesRegex(ValueError,'inherited'):tool.prescribed_flows(*args)

    def test_cycles_duplicate_peers_and_uncovered_ports_reject(self):
        args=self.graph();args[2].append(('co','ai'))
        with self.assertRaisesRegex(ValueError,'Cycle'):tool.prescribed_flows(*args)
        args=self.graph();args[2].append(('ab','ci'))
        with self.assertRaisesRegex(ValueError,'peer'):tool.prescribed_flows(*args)
        args=self.graph();args[3].pop('co')
        with self.assertRaisesRegex(ValueError,'coverage'):tool.prescribed_flows(*args)

    def test_saved_native_split_keeps_two_pressure_paths_unknown(self):
        spec=fixtures.RectangularCrossTests().fixture();spec['port_directions']={'main-a':'SINK','main-b':'SOURCE','branch':'SOURCE'}
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'runs') as folder:
            folder=Path(folder);source=folder/'project.json';source.write_text(json.dumps(spec));rectangular_tee.run(source,folder/'native');model=ifcopenshell.open(str(folder/'native/rectangular-tee.ifc'));q={'main-a':.5,'main-b':.3,'branch':.2};expected={p.GlobalId:dict(flow_m3_s=q[p.Name],source_section=p.Name,source_node='Synthetic',classification='inherited synthetic design') for p in model.by_type('IfcDistributionPort')}
            result=tool.calculate(model,expected,dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009))
            self.assertEqual(len(result['boundary_paths']),2);self.assertEqual(len(result['missing_fitting_path_losses']),2);self.assertFalse(result['pressure_budget_complete']);self.assertIsNone(result['critical_path']);self.assertEqual(result['straight_friction_subtotal_Pa'],0)
            self.assertAlmostEqual(result['boundary_inlet_flow_m3_s'],.5)
            port=next(p for p in model.by_type('IfcDistributionPort') if p.Name=='branch');self.assertAlmostEqual(result['port_flows'][port.GlobalId]['actual_velocity_m_s'],.2/(.6*.3))
            changed=copy.deepcopy(expected);changed[port.GlobalId]['flow_m3_s']+=.01
            with self.assertRaisesRegex(ValueError,'inherited'):tool.calculate(model,changed,dict(density_kg_m3=1.2,viscosity_Pa_s=1.81e-5,roughness_m=.00009))

    def test_saved_unknown_loss_cannot_be_relabelled_zero_or_complete(self):
        # Receipt-field controls only; full native replay has separate actual execution evidence.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'runs') as folder:
            folder=Path(folder);source=folder/'source';source.mkdir();out=folder/'review';out.mkdir()
            for name in ('network.json','Supply Network.ifc'):(source/name).write_text('Receipt control stub; no native geometry claim')
            fresh=dict(pressure_budget_complete=False,design_accepted=False,missing_fitting_path_losses=[dict(coefficient=None)])
            pins={str(p):tool.digest(p) for p in [source/'network.json',source/'Supply Network.ifc',*tool.methods()]}
            for change in ('completed','zero'):
                record=dict(fresh,source=str(source),inputs=pins,complete_network=False)
                if change=='completed':record['pressure_budget_complete']=True
                else:record['missing_fitting_path_losses']=[dict(coefficient=0)]
                (out/'analysis.json').write_text(json.dumps(record))
                with patch.object(tool.producer,'verify',return_value=dict(integrity_pass=True)),patch.object(tool,'prepare',return_value=(fresh,[])):
                    with self.assertRaisesRegex(ValueError,'replay differs'):tool.verify(out)


if __name__=='__main__':unittest.main()
