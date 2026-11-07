import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.coordination import compile_model,run,reconcile
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'examples/office-electrical/project.json'
GEOMETRY=ROOT/'examples/office-electrical/geometry.json'


class CoordinationTests(unittest.TestCase):
    def test_bridge_uses_shared_values_and_centre_reference(self):
        p=json.loads(PROJECT.read_text());g=json.loads(GEOMETRY.read_text())
        model=compile_model(p,g)
        first=model['devices'][0]
        self.assertEqual(first['origin_m'],[1.7,2.7,2.7])
        self.assertEqual(first['electrical_kw'],p['devices'][0]['electrical_kw'])
        self.assertEqual(first['system'],p['devices'][0]['circuit'])
        self.assertEqual(first['properties']['PowerFactor'],0.9)
        p['devices'][0].update(x_m=3,electrical_kw=0.06,power_factor=0.95)
        updated=compile_model(p,g)['devices'][0]
        self.assertEqual(updated['origin_m'][0],2.7)
        self.assertEqual(updated['electrical_kw'],0.06)
        self.assertEqual(updated['properties']['PowerFactor'],0.95)

    def test_missing_envelope_and_duplicate_engineering_fields_rejected(self):
        p=json.loads(PROJECT.read_text());g=json.loads(GEOMETRY.read_text())
        for change in (lambda x:x['devices'].pop(),lambda x:x['devices'][0].update(electrical_kw=0.5),
                       lambda x:x['devices'][0].update(x_m=999),lambda x:x.update(xy_reference='minimum corner')):
            candidate=copy.deepcopy(g);change(candidate)
            with self.assertRaises(ProjectError):compile_model(p,candidate)

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'optional IFC dependency')
    def test_saved_artifacts_reconcile_and_tampering_is_detected(self):
        import ifcopenshell
        import ifcopenshell.api
        p=json.loads(PROJECT.read_text())
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run';result=run(PROJECT,GEOMETRY,out)
            self.assertTrue(result['calculated_checks_pass'])
            self.assertEqual(len(result['devices']),3)
            self.assertFalse(result['design_accepted'])
            ifc=out/'bim/model.ifc';dxf=out/'electrical/devices.dxf';calc=out/'electrical/calculations.json'
            original=calc.read_bytes();bad=json.loads(original)
            bad['circuits'][0]['connected_va']+=1
            calc.write_text(json.dumps(bad))
            with self.assertRaises(ProjectError):reconcile(p,ifc,dxf,calc)
            calc.write_bytes(original)
            model=ifcopenshell.open(ifc);light=model.by_type('IfcLightFixture')[0]
            ps=next(r.RelatingPropertyDefinition for r in light.IsDefinedBy if r.is_a('IfcRelDefinesByProperties') and r.RelatingPropertyDefinition.Name=='BSA_DesignInputs')
            ifcopenshell.api.run('pset.edit_pset',model,pset=ps,properties={'ElectricalInput_kW':99.0})
            model.write(str(ifc))
            with self.assertRaises(ProjectError):reconcile(p,ifc,dxf,calc)

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'optional IFC dependency')
    def test_revised_electrical_input_propagates_to_all_outputs(self):
        p=json.loads(PROJECT.read_text());g=json.loads(GEOMETRY.read_text())
        p['devices'][0].update(id='L1.1',x_m=3,electrical_kw=0.06,power_factor=0.95)
        g['devices'][0]['id']='L1.1'
        p['circuits'][0].update(phase='L2',breaker_a=3)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);project=root/'project.json';geometry=root/'geometry.json'
            project.write_text(json.dumps(p));geometry.write_text(json.dumps(g))
            result=run(project,geometry,root/'run')
            self.assertTrue(result['calculated_checks_pass'])
            device=next(d for d in result['devices'] if d['id']=='L1.1')
            self.assertAlmostEqual(device['x_m'],3)
            self.assertEqual(device['electrical_kw'],0.06)
            self.assertEqual(device['power_factor'],0.95)


if __name__=='__main__':unittest.main()
