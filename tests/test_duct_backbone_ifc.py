import copy
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from bsa.duct_backbone_ifc import compile_model,inspect_saved,export_storey
from bsa.bim import run
from unittest.mock import patch
from bsa.cli import digest
from tests import test_duct_system_paths as fixtures

ROOT=Path(__file__).resolve().parents[1]


class DuctBackboneIFCTests(unittest.TestCase):
    def setUp(self):
        self.junction,self.schedule=fixtures.DuctSystemPathsTests().source()
        self.basis=dict(project_uuid='e307360f-2365-4f9a-8f78-d96dfba5fddb',
            elevation_m=dict(value=0,classification='assumed',source='Synthetic reference plane,not an installed level'),
            wall_thickness_m=dict(value=.001,classification='assumed',source='Synthetic wall gauge,not fabrication specification'),
            profile_interpretation=dict(value='scheduled_nominal_as_clear_internal',classification='assumed',source='Synthetic dimension convention'))

    def test_source_coverage_dimensions_and_unlinked_scope(self):
        model=compile_model(self.junction,self.schedule,self.basis)
        self.assertEqual(len(model['devices']),5);self.assertEqual(model['connections'],[])
        self.assertEqual(model['spaces'][0]['id'],'COORDINATION-ENVELOPE-NOT-ROOM')
        self.assertTrue(all(not d['properties']['PhysicalTrimmedLengthKnown'] for d in model['devices']))
        for device in model['devices']:
            self.assertEqual(device['properties']['SourceSectionID'],device['id'])
            self.assertEqual(len(device['ports']),2)

    def test_missing_assumptions_wrong_dimensions_and_source_flow_reject(self):
        for field in ('elevation_m','wall_thickness_m','profile_interpretation'):
            basis=copy.deepcopy(self.basis);basis.pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):compile_model(self.junction,self.schedule,basis)
        basis=copy.deepcopy(self.basis);basis['profile_interpretation']['value']='unknown'
        with self.assertRaises(ValueError):compile_model(self.junction,self.schedule,basis)
        schedule=copy.deepcopy(self.schedule);schedule['sections'][0]['inputs']['flow_m3_s']*=2
        with self.assertRaises(ValueError):compile_model(self.junction,schedule,self.basis)

    def test_real_saved_native_walls_stable_ids_and_tampered_metadata_reject(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            root=Path(temp);model=compile_model(self.junction,self.schedule,self.basis)
            source=root/'model.json';source.write_text(json.dumps(model));result=run(source,root/'first')
            self.assertTrue(result['model_checks_pass'])
            self.assertTrue(all(d['rectangular_checks']['closed_mesh'] for d in result['devices']))
            saved=root/'first/model.ifc';check=inspect_saved(saved,model,self.junction,self.schedule)
            self.assertEqual(check['port_count'],10);self.assertEqual(check['logical_connection_count'],0)
            exported=root/'exported.ifc';export_storey(saved,exported)
            self.assertEqual(ifcopenshell.open(str(exported)).by_type('IfcSpace'),[])
            self.assertEqual(inspect_saved(exported,model,self.junction,self.schedule,storey_container=True)['section_count'],5)
            repeated=run(source,root/'second')
            self.assertEqual({d['id']:d['global_id'] for d in result['devices']},{d['id']:d['global_id'] for d in repeated['devices']})
            file=ifcopenshell.open(str(saved));prop=next(p for p in file.by_type('IfcPropertySingleValue') if p.Name=='DesignFlow_m3_s');prop.NominalValue.wrappedValue=99
            file.write(str(root/'bad.ifc'))
            with self.assertRaisesRegex(ValueError,'flow or nominal'):inspect_saved(root/'bad.ifc',model,self.junction,self.schedule)

    def test_late_basis_mutation_prevents_complete_backbone_record(self):
        from bsa.duct_backbone_ifc import run as backbone
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temp:
            root=Path(temp);workflow=root/'workflow';(workflow/'sizing').mkdir(parents=True)
            plan=root/'plan.json';plan.write_text('{}');basis=root/'basis.json';basis.write_text(json.dumps(self.basis))
            sizing=workflow/'sizing/results.json';sizing.write_text(json.dumps(self.schedule))
            record=dict(inputs={str(plan):digest(plan)},artifact_hashes={'sizing/results.json':digest(sizing)},requirements=[])
            (workflow/'workflow.json').write_text(json.dumps(record))
            def junction(plan,workflow,native,out):
                out.parent.mkdir(parents=True);out.write_text('{}')
                return dict(self.junction,lineage=['native','sheet','sizing'],inputs={str(sizing):digest(sizing)})
            def mutate(*args):
                result=run(*args);basis.write_text(basis.read_text()+' ');return result
            # Ancestry plumbing is mocked;native wall authoring is real. Actual
            # complete AutoCAD-backed ancestry is exercised in the private replay.
            with patch('bsa.delivery.context',return_value=({},record,dict(integrity_pass=True))),patch('bsa.workflow.verify',return_value=dict(integrity_pass=True)),patch('bsa.duct_backbone_ifc.from_workflow',side_effect=junction),patch('bsa.duct_backbone_ifc.bim.run',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'changed during'):backbone(plan,workflow,'native',basis,root/'out')
            self.assertFalse((root/'out/backbone.json').exists())
