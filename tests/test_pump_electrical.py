import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bsa.engine import ProjectError
from bsa.cli import digest
from bsa.pump_electrical import run,read_pump,validate_link

ROOT=Path(__file__).resolve().parents[1]


class PumpLinkTests(unittest.TestCase):
    def test_explicit_load_position_pf_and_identity_contract(self):
        original=json.loads((ROOT/'examples/water-riser/pump-electrical-link.json').read_text())
        for update in ({'operating_power_factor':True},{'operating_power_factor':1.1},
                       {'load_basis':'replace motor rating and resize breaker'}, {'pump_guid':''}, {'position_tolerance_m':1}):
            value=dict(original,**update)
            with self.assertRaises(ProjectError):validate_link(value)


@unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('fluids'),'requires IFC/network runtimes')
class PumpElectricalTests(unittest.TestCase):
    def fixture(self,root,curve_change=None):
        from bsa.pump import run as pump_run
        files={'electrical.json':'examples/water-riser/electrical.json','network.json':'docs/evidence/pump/design-network.json',
               'curve.json':'examples/water-riser/pump-curve.json','model.ifc':'docs/evidence/water-riser/selected.ifc',
               'binding.json':'examples/water-riser/binding.json','link.json':'examples/water-riser/pump-electrical-link.json'}
        for name,source in files.items():shutil.copyfile(ROOT/source,root/name)
        if curve_change:
            path=root/'curve.json';curve=json.loads(path.read_text());curve_change(curve);path.write_text(json.dumps(curve))
        pump_run(root/'network.json',root/'curve.json',root/'pump')
        return (root/'electrical.json',root/'pump/pump.json',root/'model.ifc',root/'binding.json',root/'link.json')

    def test_operating_scenario_and_saved_ifc_preserve_baseline_hardware_and_other_devices(self):
        import ifcopenshell
        import ifcopenshell.util.element as util
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);args=self.fixture(root);before={p:digest(p) for p in args}
            result=run(*args,root/'coupled')
            self.assertTrue(result['calculated_checks_pass']);self.assertTrue(result['existing_ifc_entities_unchanged'])
            self.assertFalse(result['design_accepted']);self.assertEqual(result['unbound_electrical_device_ids'],['SHAFT-L1','SHAFT-L2'])
            original=json.loads(args[0].read_text());operating=json.loads((root/'coupled/operating-electrical.json').read_text())
            self.assertEqual(original['circuits'],operating['circuits'])
            self.assertEqual(original['devices'][1:],operating['devices'][1:])
            self.assertEqual(original['devices'][0]['electrical_kw'],.75)
            point=json.loads(args[1].read_text())['operating_point'];record=result['record']
            self.assertAlmostEqual(record['bound_device_operating_current_a'],point['estimated_electrical_kw']*1000/.85/230)
            self.assertAlmostEqual(record['operating_electrical_kw'],.4378275,delta=1e-7)
            native=ifcopenshell.open(str(root/'coupled/model.ifc'));props=util.get_psets(native.by_guid(record['pump_guid']))['BSA_PumpElectrical']
            self.assertEqual(props['BaselineElectricalInput_kW'],.75)
            self.assertAlmostEqual(props['OperatingElectricalInput_kW'],point['estimated_electrical_kw'])
            self.assertEqual(props['CircuitID'],'PUMP-SUPPLY')
            self.assertTrue(all(digest(p)==sha for p,sha in before.items()))

    def test_report_scalar_and_artifact_tampering_are_rejected(self):
        for action in ('scalar','artifact','source','curve-metadata'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);args=self.fixture(root)
                if action=='scalar':
                    report=json.loads(args[1].read_text());report['operating_point']['estimated_electrical_kw']=9.99;args[1].write_text(json.dumps(report))
                elif action=='curve-metadata':
                    report=json.loads(args[1].read_text());report['curve']['speed_rpm']=9999;args[1].write_text(json.dumps(report))
                elif action=='artifact':
                    path=root/'pump/iterations.csv';path.write_bytes(path.read_bytes()+b'\n')
                else:
                    path=root/'curve.json';path.write_bytes(path.read_bytes()+b'\n')
                with self.assertRaises(ProjectError):run(*args,root/'rejected')
                self.assertFalse((root/'rejected').exists())

    def test_wrong_identity_disconnected_pump_and_wrong_xy_are_rejected(self):
        import ifcopenshell
        for action in ('identity','connection','position'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);args=self.fixture(root)
                if action=='identity':
                    link=json.loads(args[4].read_text());link['pump_guid']=ifcopenshell.open(str(args[2])).by_type('IfcSanitaryTerminal')[0].GlobalId;args[4].write_text(json.dumps(link))
                elif action=='connection':
                    native=ifcopenshell.open(str(args[2]));link=json.loads(args[4].read_text());port=native.by_guid(link['source_port_guid'])
                    for relation in list(port.ConnectedTo)+list(port.ConnectedFrom):native.remove(relation)
                    native.write(str(args[2]))
                else:
                    project=json.loads(args[0].read_text());project['devices'][0]['x_m']+=.5;args[0].write_text(json.dumps(project))
                with self.assertRaises(ProjectError):run(*args,root/'rejected')
                self.assertFalse((root/'rejected').exists())

    def test_missing_combined_efficiency_does_not_create_an_electrical_estimate(self):
        def no_efficiency(curve):
            curve['efficiency_basis']='not supplied'
            for point in curve['points']:point.pop('wire_to_water_efficiency')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);args=self.fixture(root,no_efficiency)
            with self.assertRaisesRegex(ProjectError,'combined wire-to-water'):run(*args,root/'rejected')
            self.assertFalse((root/'rejected').exists())

    def test_small_operating_current_does_not_approve_failed_baseline_design_check(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);args=self.fixture(root);project=json.loads(args[0].read_text())
            project['circuits'][0]['breaker_a']=3;args[0].write_text(json.dumps(project))
            result=run(*args,root/'coupled')
            self.assertFalse(result['baseline_checks_pass']);self.assertTrue(result['operating_checks_pass'])
            self.assertFalse(result['calculated_checks_pass']);self.assertTrue(result['baseline_hardware_retained'])
            revised=json.loads((root/'coupled/operating-electrical.json').read_text())
            self.assertEqual(revised['circuits'][0]['breaker_a'],3)

    @unittest.skipUnless(importlib.util.find_spec('manifold3d'),'requires clash runtime')
    def test_full_workflow_revised_ifc_consumers_and_integrity(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run';result=execute(ROOT/'examples/water-riser/coupled-plan.json',out)
            self.assertTrue(result['execution_pass']);self.assertTrue(verify(out)['integrity_pass'])
            self.assertEqual(result['tasks']['coupled-qa']['status'],'pass');self.assertEqual(result['tasks']['coupled-drawing']['status'],'pass')
            path=out/'coupled/model.ifc';path.write_bytes(path.read_bytes()+b'\n')
            self.assertFalse(verify(out)['integrity_pass'])


if __name__=='__main__':unittest.main()
