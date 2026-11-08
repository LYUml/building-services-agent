import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.water_binding import derive,run,reconcile,validate_contract

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/water-loop-ifc'


def inputs():
    return [json.loads((EXAMPLE/name).read_text()) for name in ('project.json','binding.json')]


class WaterBindingContractTests(unittest.TestCase):
    def test_duplicate_geometry_missing_coverage_and_reused_guid_rejected(self):
        for change in (lambda p,b:p['junctions'][0].update(elevation_m=1),
                       lambda p,b:p['pipes'][0].update(length_m=5),
                       lambda p,b:p['pipes'][0].update(diameter_m=.04),
                       lambda p,b:b['nodes'].pop('A'),
                       lambda p,b:b['pipes']['JB'].append(copy.deepcopy(b['pipes']['JA'][0])),
                       lambda p,b:b.update(node_idealization='guess node resistance'),
                       lambda p,b:b.update(project_guid='name instead of GUID')):
            p,b=inputs();change(p,b)
            with self.assertRaises(ProjectError):validate_contract(p,b)


@unittest.skipUnless(importlib.util.find_spec('ifcopenshell') and importlib.util.find_spec('wntr'),'requires BIM and water runtimes')
class SavedWaterBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bsa.bim import run as author
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.authored=author(EXAMPLE/'model.json',cls.root/'model')
        cls.ifc=cls.root/'model/model.ifc'

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def mutated(self,change):
        import ifcopenshell
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        model=ifcopenshell.open(str(self.ifc));change(model)
        path=Path(folder.name)/'changed.ifc';model.write(str(path));return path

    def test_real_profiles_chains_elevations_and_reverse_flow(self):
        p,b=inputs();derived,e=derive(self.ifc,p,b)
        self.assertTrue(self.authored['model_checks_pass'])
        self.assertEqual(e['selected_element_count'],12);self.assertEqual(e['connection_pair_count'],12)
        self.assertEqual({r['id']:r['length_m'] for r in derived['pipes']},{'JA':5,'JB':7,'AC':7,'CB':5})
        self.assertTrue(all(abs(r['diameter_m']-.04)<1e-9 for r in derived['pipes']))
        self.assertEqual({r['id']:r['elevation_m'] for r in derived['junctions']},{'J0':1,'A':1,'B':3,'C':3})
        from bsa.ifc_drawing import extract
        drawing=extract(self.ifc)
        self.assertTrue(drawing['calculated_checks_pass']);self.assertEqual(drawing['segment_count'],6)
        self.assertTrue(all(r['sink_port_guid'] is None and r['source_port_guid'] is None for r in drawing['segments']))
        before=digest(self.ifc)
        with tempfile.TemporaryDirectory() as f:
            out=Path(f)/'run';r=run(EXAMPLE/'project.json',self.ifc,EXAMPLE/'binding.json',out)
            self.assertTrue(r['calculated_checks_pass'],r);self.assertTrue(r['ifc_copy_unchanged'])
            self.assertFalse(r['design_accepted']);self.assertEqual(digest(out/'model.ifc'),before)
            analysis=json.loads((out/'analysis/water.json').read_text())
            self.assertTrue(analysis['checks']['pipe_energy']);self.assertEqual(analysis['independent_cycle_count'],1)
            self.assertLess(next(v['flow_m3_s'] for v in analysis['pipes'] if v['id']=='CB'),0)
            import csv
            with (out/'pipe-results.csv').open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),6)
            self.assertTrue(all(row['element_guid'] and row['signed_flow_m3_s'] for row in rows))
            changed=json.loads((out/'network-input.json').read_text());changed['pipes'][0]['length_m']+=1
            (out/'network-input.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ProjectError,'saved IFC differs'):reconcile(out/'model.ifc',out/'network-input.json',p,b)
        self.assertEqual(before,digest(self.ifc))

    def test_renamed_elements_are_bound_by_guid_not_name(self):
        p,b=inputs()
        def rename(model):
            for row in model.by_type('IfcDistributionElement'):row.Name='Repeated arbitrary name';row.Tag=None
            for port in model.by_type('IfcDistributionPort'):port.Name='Repeated port name'
        derived,e=derive(self.mutated(rename),p,b)
        self.assertEqual([r['length_m'] for r in derived['pipes']],[5,7,7,5])

    def test_millimetre_ifc_converts_actual_profile_and_port_units(self):
        import ifcopenshell
        import ifcopenshell.util.unit as unit
        p,b=inputs()
        with tempfile.TemporaryDirectory() as f:
            mm=unit.convert_file_length_units(ifcopenshell.open(str(self.ifc)),'MILLIMETER')
            path=Path(f)/'mm.ifc';mm.write(str(path));derived,e=derive(path,p,b)
            self.assertEqual(e['length_unit_to_m'],.001)
            self.assertEqual([r['length_m'] for r in derived['pipes']],[5,7,7,5])
            self.assertTrue(all(abs(r['diameter_m']-.04)<1e-9 for r in derived['pipes']))

    def test_disconnection_noncoincident_node_and_extra_system_device_fail(self):
        import ifcopenshell.api as api
        p,b=inputs();g=b['pipes']['JA'][0]['end_port_guid']
        def disconnect(model):
            for rel in list(model.by_type('IfcRelConnectsPorts')):
                if g in (rel.RelatingPort.GlobalId,rel.RelatedPort.GlobalId):model.remove(rel)
        def shift(model):
            port=model.by_guid(b['nodes']['A']['port_guids'][0]);xyz=port.ObjectPlacement.RelativePlacement.Location
            xyz.Coordinates=tuple(v+(.01 if i==0 else 0) for i,v in enumerate(xyz.Coordinates))
        def extra(model):
            obj=api.run('root.create_entity',model,ifc_class='IfcPipeFitting',name='Unbound fitting')
            api.run('system.assign_system',model,products=[obj],system=model.by_guid(b['system_guid']))
        for change in (disconnect,shift,extra):
            with self.assertRaises(ProjectError):derive(self.mutated(change),p,b)

    def test_profile_metadata_and_oneway_pipe_contradictions_fail(self):
        p,b=inputs();g=b['pipes']['JA'][0]['element_guid']
        def profile(model):
            solid=model.by_guid(g).Representation.Representations[0].Items[0]
            solid.SweptArea.WallThickness*=1.5
        def oneway(model):
            ports=b['pipes']['JA'][0]
            model.by_guid(ports['start_port_guid']).FlowDirection='SINK'
            model.by_guid(ports['end_port_guid']).FlowDirection='SOURCE'
        for change in (profile,oneway):
            with self.assertRaises(ProjectError):derive(self.mutated(change),p,b)

    def test_actual_workflow_and_direct_saved_ifc_input_keep_integrity(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as f:
            root=Path(f);r=execute(EXAMPLE/'plan.json',root/'workflow')
            self.assertTrue(r['execution_pass']);self.assertTrue(verify(root/'workflow')['integrity_pass'])
            for name in ('project.json','binding.json','brief.md'):(root/name).write_bytes((EXAMPLE/name).read_bytes())
            (root/'source.ifc').write_bytes(self.ifc.read_bytes())
            plan=json.loads((EXAMPLE/'plan.json').read_text());plan['tasks']=plan['tasks'][1:]
            plan['tasks'][0].pop('depends_on');plan['tasks'][0]['ifc']='source.ifc'
            plan['requirements']=plan['requirements'][1:];plan['passage_dispositions']['P002']='context'
            path=root/'plan.json';path.write_text(json.dumps(plan));r=execute(path,root/'direct')
            self.assertTrue(r['execution_pass']);self.assertTrue(verify(root/'direct')['integrity_pass'])
            (root/'direct/water/model.ifc').write_text('tampered')
            self.assertFalse(verify(root/'direct')['integrity_pass'])
