import json
import math
import unittest
from bsa.spatial_stub_friction import point,run,verify
from bsa.spatial_terminal_stubs import run as author_stubs
from bsa.workflow import execute
from tests import test_spatial_terminal_inlet_workflow as fixtures

class StraightFrictionPointTests(unittest.TestCase):
    def test_laminar_matches_independent_poiseuille_and_keeps_gravity_separate(self):
        q=.1;d=.1;length=2;rho=1.25;mu=1.8e-5
        r=point(q,d,length,rho,mu,0,-.5);expected=128*mu*length*(q/1000)/(math.pi*d**4)
        self.assertAlmostEqual(r['straight_friction_Pa'],expected,places=14);self.assertAlmostEqual(r['signed_geometric_rho_g_dz_Pa'],-rho*9.80665*.5);self.assertEqual(r['regime'],'laminar 64/Re')

    def test_turbulent_factor_satisfies_independent_colebrook_residual(self):
        r=point(100,.2,.15,1.25,1.8e-5,.00009,-.15);f=r['darcy_friction_factor'];re=r['reynolds'];residual=1/math.sqrt(f)+2*math.log10(r['relative_roughness']/3.7+2.51/(re*math.sqrt(f)))
        self.assertAlmostEqual(residual,0,places=10);self.assertGreater(r['straight_friction_Pa'],0)

    def test_transitional_case_stays_unknown_and_unsupported_inputs_reject(self):
        q=3000*1.8e-5*math.pi*.1/(4*1.25)*1000;r=point(q,.1,1,1.25,1.8e-5,0,0)
        self.assertEqual(r['status'],'pending');self.assertIsNone(r['straight_friction_Pa']);self.assertIsNone(r['darcy_friction_factor'])
        for args in [(-1,.1,1,1.25,1.8e-5,0,0),(1,.1,1,1.25,1.8e-5,.006,0)]:
            with self.assertRaises(ValueError):point(*args)

class NativeStubFrictionTests(unittest.TestCase):
    def test_native_geometry_density_flow_inheritance_and_mutation_reject(self):
        fixture=fixtures.InletWorkflowTests();f,_=fixture.setup_plan();self.addCleanup(fixture.doCleanups)
        out=f.root/'workflow';execute(f.plan,out,module_providers={'recognition':'ifcopenshell.polygon-spaces'})
        inlet=json.loads((out/'inlets/terminal-inlets.json').read_text());stub_basis={row['terminal']:dict(length_m=dict(value=.15,unit='m',source='Synthetic short length',classification='design_choice'),internal_diameter_m=dict(value=row['diameter_m'],unit='m',source='Synthetic bore equals nominal assumption',classification='assumed'),wall_thickness_m=dict(value=.0008,unit='m',source='Synthetic wall choice',classification='design_choice')) for row in inlet['inlets']};path=f.root/'stubs.json';path.write_text(json.dumps(stub_basis));stubs=f.root/'stubs';source=author_stubs(out/'inlets/terminal-inlets.json',path,stubs)
        basis=f.root/'air.json';basis.write_text(json.dumps(dict(dynamic_viscosity_pa_s=dict(value=1.8e-5,unit='Pa.s',source='Synthetic viscosity',classification='assumed'),roughness_m=dict(value=.00009,unit='m',source='Synthetic roughness',classification='assumed'))))
        result=run(stubs/'terminal-stubs.json',basis,f.root/'friction');verify(f.root/'friction');self.assertEqual(result['calculation']['engineering_status'],'pending');self.assertFalse(result['calculation']['whole_system_pressure_complete'])
        for native in source['stubs']:
            row=result['calculation']['terminals'][native['terminal']];self.assertAlmostEqual(row['native_length_m'],.15);self.assertEqual(row['cases']['maximum']['flow_L_s'],native['maximum_flow_L_s']);self.assertEqual(row['inherited_density']['value'],1.25);self.assertEqual(row['inherited_density']['classification'],'assumed');self.assertEqual(row['inherited_stub_basis']['internal_diameter_m']['classification'],'assumed')
        report=f.root/'friction/straight-friction.json';data=json.loads(report.read_text());next(iter(data['calculation']['terminals'].values()))['cases']['maximum']['straight_friction_Pa']+=1;report.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'source/native replay'):verify(report.parent)
        spec=json.loads(basis.read_text());spec['density_kg_m3']=1.2;basis.write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError,'replacement'):run(stubs/'terminal-stubs.json',basis,f.root/'rejected')
        self.assertFalse((f.root/'rejected').exists())
