from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

from bsa.workflow import execute,validate_plan,verify
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class RouteWorkflowTests(unittest.TestCase):
    def test_operating_bim_state_requires_passing_fan_and_gates_drawing(self):
        plan=ROOT/'examples/route-search/port-airflow-state-plan.json';validate_plan(plan)
        for fault in ('none','fan','state'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                out=(Path(folder)/'run').resolve()
                with patch('bsa.bim.run',return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_join.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_material.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_pressure.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.circular_fan_selection.run',return_value={'status':'pass','scope':'dispatch-only test'}),patch('bsa.circular_fan_selection.run_selected',return_value={'calculated_checks_pass':fault!='fan','scope':'dispatch-only test'}),patch('bsa.circular_fan_metadata.run',return_value={'calculated_checks_pass':fault!='state','scope':'dispatch-only test'}) as state,patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                    result=execute(plan,out)
                if fault=='fan':state.assert_not_called()
                else:self.assertEqual(state.call_args.args,(out/'fan',out/'state'))
                if fault=='none':self.assertEqual(result['tasks']['drawing']['status'],'pass')
                else:drawing.assert_not_called()
                self.assertEqual(result['tasks']['review']['status'],'pending')

    def test_circular_catalogue_selection_handoff_and_failure_gates(self):
        plan=ROOT/'examples/route-search/port-fan-selection-plan.json';validate_plan(plan)
        for fault in ('none','selection'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                out=(Path(folder)/'run').resolve()
                with patch('bsa.bim.run',return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_join.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_material.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_pressure.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.circular_fan_selection.run',return_value={'status':'pass' if fault=='none' else 'fail','scope':'dispatch-only test'}) as screen,patch('bsa.circular_fan_selection.run_selected',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}) as consume,patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                    result=execute(plan,out)
                self.assertEqual(screen.call_args.args[0],out/'pressure')
                if fault=='none':
                    self.assertEqual(consume.call_args.args[:2],(out/'selection',out/'pressure'))
                    self.assertEqual(result['tasks']['drawing']['status'],'pass')
                else:consume.assert_not_called();drawing.assert_not_called()
                self.assertEqual(result['tasks']['review']['status'],'pending')

    def test_circular_fan_inherits_pressure_and_failed_capacity_blocks_drawing(self):
        plan=ROOT/'examples/route-search/port-fan-plan.json';validate_plan(plan)
        for fault in ('none','pressure','fan'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                out=(Path(folder)/'run').resolve()
                with patch('bsa.bim.run',return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_join.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_material.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_pressure.run',return_value={'calculated_checks_pass':fault!='pressure','scope':'dispatch-only test'}),patch('bsa.circular_fan.run',return_value={'calculated_checks_pass':fault!='fan','scope':'dispatch-only test'}) as fan,patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                    result=execute(plan,out)
                if fault=='pressure':fan.assert_not_called()
                else:
                    self.assertEqual(fan.call_args.args[0],out/'pressure')
                    self.assertEqual(fan.call_args.args[2],out/'fan')
                if fault=='none':self.assertEqual(result['tasks']['drawing']['status'],'pass')
                else:drawing.assert_not_called()
                self.assertEqual(result['tasks']['review']['status'],'pending')

    def test_extended_pressure_inherits_material_and_blocks_drawing_on_failure(self):
        plan=ROOT/'examples/route-search/port-pressure-plan.json';validate_plan(plan)
        for fault in ('none','material','pressure'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                out=(Path(folder)/'run').resolve()
                with patch('bsa.bim.run',return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_join.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_material.run',return_value={'calculated_checks_pass':fault!='material','scope':'dispatch-only test'}),patch('bsa.route_pressure.run',return_value={'calculated_checks_pass':fault!='pressure','scope':'dispatch-only test'}) as pressure,patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                    result=execute(plan,out)
                if fault=='material':pressure.assert_not_called()
                else:
                    self.assertEqual(pressure.call_args.args[0],out/'material')
                    self.assertEqual(pressure.call_args.args[2],out/'pressure')
                if fault=='none':self.assertEqual(result['tasks']['drawing']['status'],'pass')
                else:drawing.assert_not_called()
                self.assertEqual(result['tasks']['review']['status'],'pending')

    def test_material_qa_receives_exact_join_and_gates_route_drawing(self):
        plan=ROOT/'examples/route-search/port-material-plan.json'
        validate_plan(plan)
        for fault in ('none','pressure','material'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                out=(Path(folder)/'run').resolve()
                with patch('bsa.bim.run',return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':fault!='pressure','scope':'dispatch-only test'}),patch('bsa.route_join.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}),patch('bsa.route_material.run',return_value={'calculated_checks_pass':fault!='material','scope':'dispatch-only test'}) as material,patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                    result=execute(plan,out)
                if fault=='pressure':material.assert_not_called()
                else:
                    self.assertEqual(material.call_args.args[0],out/'join')
                    self.assertEqual(material.call_args.args[2],out/'material')
                if fault=='none':self.assertEqual(result['tasks']['drawing']['status'],'pass')
                else:drawing.assert_not_called()
                self.assertEqual(result['tasks']['review']['status'],'pending')

    def test_joined_route_inherits_producer_and_gates_drawing(self):
        plan=ROOT/'examples/route-search/port-joined-plan.json'
        validate_plan(plan)
        for fault in ('none','pressure','join'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                out=(Path(folder)/'run').resolve()
                with patch('bsa.bim.run',return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':fault!='pressure','scope':'dispatch-only test'}),patch('bsa.route_join.run',return_value={'calculated_checks_pass':fault!='join','scope':'dispatch-only test'}) as join,patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                    result=execute(plan,out)
                if fault=='pressure':join.assert_not_called()
                else:self.assertEqual(join.call_args.args,(out/'route',out/'join'))
                if fault=='none':self.assertEqual(result['tasks']['drawing']['status'],'pass')
                else:
                    drawing.assert_not_called()
                    self.assertEqual(result['tasks']['drawing']['status'],'pending')
                self.assertEqual(result['tasks']['review']['status'],'pending')

    def test_port_route_rejects_copied_endpoints_and_replacement_ifc(self):
        source=ROOT/'examples/route-search/port-routing-plan.json'
        _,inputs=validate_plan(source)
        for fault in ('endpoints','replacement'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                root=Path(folder)
                for path in inputs:
                    if path.parent==source.parent:shutil.copy2(path,root/path.name)
                plan=json.loads(source.read_text())
                if fault=='replacement':plan['tasks'][1]['ifc']='port-source-model.json'
                else:
                    template=root/'port-routing-template.json';data=json.loads(template.read_text());data['start_m']=[0,1.5];template.write_text(json.dumps(data))
                target=root/'plan.json';target.write_text(json.dumps(plan))
                with self.assertRaises(ProjectError):validate_plan(target)

    def test_source_port_route_inherits_exact_native_source_and_selected_model(self):
        plan=ROOT/'examples/route-search/port-routing-plan.json'
        validate_plan(plan)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=(Path(folder)/'run').resolve()
            with patch('bsa.bim.run',return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':True,'scope':'dispatch-only test'}) as route,patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                result=execute(plan,out)
            self.assertEqual(route.call_args.args[0],out/'source/model.ifc')
            self.assertEqual(drawing.call_args.args[0],out/'route/route/selected/bound/bim/model.ifc')
            self.assertEqual(drawing.call_args.args[1],out/'route/route/selected/model-input.json')
            self.assertEqual(result['tasks']['review']['status'],'pending')

    def test_source_port_failure_gates(self):
        plan=ROOT/'examples/route-search/port-routing-plan.json'
        for fault in ('source','pressure'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
                with patch('bsa.bim.run',side_effect=ProjectError('native source invalid') if fault=='source' else None,return_value={}),patch('bsa.route_ports.run',return_value={'calculated_checks_pass':False,'scope':'dispatch-only test'}) as route,patch('bsa.ifc_route_drawing.run') as drawing:
                    result=execute(plan,Path(folder)/'run')
                if fault=='source':route.assert_not_called()
                else:self.assertEqual(result['tasks']['route']['status'],'fail')
                drawing.assert_not_called()
                self.assertEqual(result['tasks']['drawing']['status'],'pending')

    def test_generated_route_model_is_inherited_by_drawing(self):
        plan=ROOT/'examples/route-search/vertical-air-plan.json'
        validate_plan(plan)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=(Path(folder)/'run').resolve()
            with patch('bsa.route_optimize.run',return_value={'calculated_checks_pass':True}),patch('bsa.ifc_route_drawing.run',return_value={'calculated_checks_pass':True}) as drawing:
                result=execute(plan,out)
            self.assertEqual(drawing.call_args.args[0],out/'route/selected/bound/bim/model.ifc')
            self.assertEqual(drawing.call_args.args[1],out/'route/selected/model-input.json')
            self.assertEqual(result['tasks']['drawing']['status'],'pass')
            self.assertEqual(result['tasks']['review']['status'],'pending')
            self.assertFalse(result['design_accepted'])

    def test_failed_route_pressure_blocks_inherited_drawing(self):
        plan=ROOT/'examples/route-search/vertical-air-plan.json'
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            with patch('bsa.route_optimize.run',return_value={'calculated_checks_pass':False}),patch('bsa.ifc_route_drawing.run',side_effect=AssertionError('failed pressure must block drawing')) as drawing:
                result=execute(plan,Path(folder)/'run')
            drawing.assert_not_called()
            self.assertEqual(result['tasks']['drawing']['status'],'pending')

    def test_route_inputs_are_tracked_and_failed_pressure_blocks_clash(self):
        plan=ROOT/'examples/route-search/coordination-plan.json'
        _,inputs=validate_plan(plan)
        for name in ('route-input.json','model-settings.json','network.json','self-clash-policy.json'):
            self.assertIn((plan.parent/name).resolve(),inputs)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            with patch('bsa.route_optimize.run',return_value={'calculated_checks_pass':False}),patch('bsa.clash.run',side_effect=AssertionError('failed producer must block clash')) as clash:
                result=execute(plan,Path(folder)/'run')
            clash.assert_not_called()
            self.assertEqual(result['tasks']['route']['status'],'fail')
            self.assertEqual(result['tasks']['self-qa']['status'],'pending')
            self.assertEqual(result['tasks']['review']['status'],'pending')
            self.assertTrue(verify(Path(folder)/'run')['integrity_pass'])

    def test_passing_producer_uses_registered_selected_ifc_path(self):
        plan=ROOT/'examples/route-search/coordination-plan.json'
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            out=(Path(folder)/'run').resolve()
            with patch('bsa.route_optimize.run',return_value={'calculated_checks_pass':True}),patch('bsa.clash.run',return_value={'calculated_checks_pass':True}) as clash:
                result=execute(plan,out)
            self.assertEqual(clash.call_args.args[0],out/'route/selected/bound/bim/model.ifc')
            self.assertEqual(result['tasks']['self-qa']['status'],'pass')
            self.assertFalse(result['design_accepted'])
