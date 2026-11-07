import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from bsa.engine import ProjectError
from bsa.ifc_drawing import extract, run, validate_settings

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/evidence/water-riser/selected.ifc'


class DrawingSettingsTests(unittest.TestCase):
    def test_invalid_axes_height_and_source(self):
        for update in ({'projection_axes':['Z','Z']},{'projection_axes':[[], 'X']},
                       {'annotation_height_m':True},{'source':''}):
            settings=dict(projection_axes=['X','Z'],annotation_height_m=.12,source='synthetic test')
            settings.update(update)
            with self.assertRaises(ProjectError):validate_settings(settings)


@unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'requires IFC runtime')
class SavedIFCDrawingTests(unittest.TestCase):
    def test_workflow_direct_ifc_sources_preserve_requirement_passage_mapping(self):
        from bsa.workflow import execute,verify
        from bsa.cli import digest
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'source.ifc').write_bytes(SOURCE.read_bytes())
            (root/'settings.json').write_text(json.dumps(dict(projection_axes=['X','Z'],annotation_height_m=.12,source='synthetic direct IFC test')))
            brief=root/'brief.md';brief.write_text('Read the existing saved IFC and retain source-linked evidence.\n')
            tasks=[dict(id='drawing',kind='ifc_drawing',ifc='source.ifc',settings='settings.json')]
            if importlib.util.find_spec('manifold3d'):
                (root/'policy.json').write_bytes((ROOT/'examples/water-riser/policy.json').read_bytes())
                tasks.append(dict(id='qa',kind='ifc_clash',ifc='source.ifc',policy='policy.json'))
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=tasks,
                      requirements=[dict(id='R'+str(i),passage='P001',quote='Read the existing saved IFC and retain source-linked evidence.',task=t['id'],acceptance='Scoped source extraction/checks only') for i,t in enumerate(tasks)])
            path=root/'plan.json';path.write_text(json.dumps(plan));result=execute(path,root/'run')
            self.assertTrue(result['execution_pass']);self.assertTrue(verify(root/'run')['integrity_pass'])

    def test_saved_profiles_drive_schedule_and_reopened_dxf(self):
        import ezdxf
        before=SOURCE.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);settings=root/'settings.json'
            settings.write_text(json.dumps(dict(projection_axes=['X','Z'],annotation_height_m=.12,source='synthetic test')))
            result=run(SOURCE,settings,root/'drawing')
            self.assertTrue(result['calculated_checks_pass']);self.assertFalse(result['design_accepted'])
            self.assertEqual(result['segment_count'],2)
            self.assertEqual(len(result['excluded_non_segment_elements']),2)
            self.assertAlmostEqual(sum(r['length_m'] for r in result['segments']),5)
            for row in result['segments']:
                self.assertAlmostEqual(row['inner_diameter_m'],.032)
                self.assertAlmostEqual(row['outside_diameter_m'],.04)
                self.assertAlmostEqual(row['analytic_wall_volume_m3'],math.pi*(.04**2-.032**2)*2.5/4)
                self.assertAlmostEqual(math.dist(row['start_world_m'],row['end_world_m']),2.5)
            doc=ezdxf.readfile(root/'drawing/segments.dxf')
            self.assertEqual(doc.header['$INSUNITS'],6)
            lines=list(doc.modelspace().query('LINE[layer=="BSA_PIPE_AXIS"]'))
            self.assertEqual(len(lines),2)
            by_guid={row['guid']:row for row in result['segments']}
            for line in lines:
                row=by_guid[line.get_xdata('BSA_IFC')[0].value]
                self.assertAlmostEqual(line.dxf.start.x,row['start_world_m'][0])
                self.assertAlmostEqual(line.dxf.start.y,row['start_world_m'][2])
                self.assertAlmostEqual(line.dxf.end.y,row['end_world_m'][2])
            self.assertEqual(len((root/'drawing/segments.csv').read_text().splitlines()),3)
            self.assertEqual(SOURCE.read_bytes(),before)
            settings.write_text(json.dumps(dict(projection_axes=['X','Y'],annotation_height_m=.12,source='end-on negative test')))
            end_on=run(SOURCE,settings,root/'end-on')
            self.assertFalse(end_on['calculated_checks_pass'])
            self.assertIn('end-on',end_on['drawing_error'])
            self.assertFalse((root/'end-on/segments.dxf').exists())

    def test_native_millimetres_and_unsupported_or_inconsistent_geometry(self):
        import ifcopenshell
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);model=ifcopenshell.open(str(SOURCE))
            for point in model.by_type('IfcCartesianPoint'):
                point.Coordinates=tuple(v*1000 for v in point.Coordinates)
            for solid in model.by_type('IfcExtrudedAreaSolid'):solid.Depth*=1000
            for profile in model.by_type('IfcCircleHollowProfileDef'):
                profile.Radius*=1000;profile.WallThickness*=1000
            next(u for u in model.by_type('IfcSIUnit') if u.UnitType=='LENGTHUNIT').Prefix='MILLI'
            path=root/'millimetres.ifc';model.write(str(path));result=extract(path)
            self.assertTrue(result['calculated_checks_pass'])
            self.assertEqual(result['source_length_unit_to_m'],.001)
            self.assertAlmostEqual(result['segments'][0]['length_m'],2.5)
            self.assertAlmostEqual(result['segments'][0]['inner_diameter_m'],.032)
            for prop in model.by_type('IfcPropertySingleValue'):
                if prop.Name=='InternalDiameter_m':prop.NominalValue.wrappedValue=.099
            model.write(str(path));result=extract(path)
            self.assertFalse(result['calculated_checks_pass'])
            self.assertEqual(len(result['unsupported_segments']),2)
            model=ifcopenshell.open(str(SOURCE))
            model.by_type('IfcPipeSegment')[0].Representation=None;model.write(str(path))
            result=extract(path)
            self.assertFalse(result['calculated_checks_pass'])
            self.assertEqual(len(result['unsupported_segments']),1)

    def test_workflow_dependency_and_drawing_artifact_integrity(self):
        from bsa.workflow import execute, verify, validate_plan
        from bsa.cli import digest
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'brief.md').write_text('Draw saved IFC segments from explicit profiles and ports.\n')
            (root/'model.json').write_bytes((ROOT/'examples/water-riser/model.json').read_bytes())
            (root/'settings.json').write_text(json.dumps(dict(projection_axes=['X','Z'],annotation_height_m=.12,source='synthetic test')))
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(root/'brief.md'),passage_dispositions={'P001':'requirement'},
                      tasks=[dict(id='model',kind='bim',project='model.json'),dict(id='drawing',kind='ifc_drawing',depends_on='model',settings='settings.json')],
                      requirements=[dict(id='R'+str(i),passage='P001',quote='Draw saved IFC segments from explicit profiles and ports.',task=task,acceptance='Source profiles to schematic; native/visual review pending') for i,task in enumerate(('model','drawing'))])
            path=root/'plan.json';path.write_text(json.dumps(plan));result=execute(path,root/'run')
            self.assertTrue(result['execution_pass']);self.assertTrue(verify(root/'run')['integrity_pass'])
            output=root/'run/drawing/segments.dxf';output.write_bytes(output.read_bytes()+b'\n')
            self.assertFalse(verify(root/'run')['integrity_pass'])
            plan['tasks'][1]['depends_on']='drawing';path.write_text(json.dumps(plan))
            with self.assertRaises(ProjectError):validate_plan(path)

    def test_rotated_product_placement_preserves_true_length_and_port_world_points(self):
        import ifcopenshell
        with tempfile.TemporaryDirectory() as folder:
            model=ifcopenshell.open(str(SOURCE));pipe=model.by_type('IfcPipeSegment')[0]
            relative=pipe.ObjectPlacement.RelativePlacement
            relative.Axis.DirectionRatios=(.6,0.,.8)
            relative.RefDirection.DirectionRatios=(0.,1.,0.)
            path=Path(folder)/'rotated.ifc';model.write(str(path));result=extract(path)
            self.assertTrue(result['calculated_checks_pass'])
            row=next(r for r in result['segments'] if r['guid']==pipe.GlobalId)
            self.assertAlmostEqual(row['length_m'],2.5)
            delta=[b-a for a,b in zip(row['start_world_m'],row['end_world_m'])]
            self.assertAlmostEqual(abs(delta[0]),1.5)
            self.assertAlmostEqual(abs(delta[2]),2)

    def test_plain_ifc_profiles_do_not_require_project_specific_properties(self):
        import ifcopenshell
        import ifcopenshell.api
        from bsa.cli import digest
        with tempfile.TemporaryDirectory() as folder:
            model=ifcopenshell.open(str(SOURCE))
            for pipe in model.by_type('IfcPipeSegment'):
                for relation in list(pipe.IsDefinedBy):
                    if relation.is_a('IfcRelDefinesByProperties') and relation.RelatingPropertyDefinition.Name=='BSA_DesignInputs':
                        ifcopenshell.api.run('pset.remove_pset',model,product=pipe,pset=relation.RelatingPropertyDefinition)
            path=Path(folder)/'plain.ifc';model.write(str(path));result=extract(path)
            self.assertTrue(result['calculated_checks_pass'])
            self.assertEqual(len(result['segments']),2)
            for row in result['segments']:
                self.assertAlmostEqual(row['inner_diameter_m'],.032)
                self.assertIn(digest(path),row['source'])
                self.assertEqual(len(row['missing_diameter_metadata']),2)


if __name__=='__main__':unittest.main()
