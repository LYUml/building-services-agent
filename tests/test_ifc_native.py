import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import ezdxf
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_native import validate_settings, validate_contours, verify_dxf, run
from bsa.native_cad import DEFAULT_EXE

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/evidence/ifc-drawing/segments.dxf'
SETTINGS=ROOT/'examples/water-riser/native-sheet.json'


class NativeDiagramTests(unittest.TestCase):
    def test_closed_contours_validate_and_native_reconciliation_rejects_mutations(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);doc=ezdxf.new('R2018');doc.units=6;doc.appids.new('BSA_IFC')
            poly=doc.modelspace().add_lwpolyline([(0,0),(2,0),(2,1),(0,1)],close=True)
            poly.set_xdata('BSA_IFC',[(1000,'fictional-contour')]);validate_contours(doc)
            original=root/'original.dxf';doc.saveas(original)
            rounded=ezdxf.readfile(original);p=rounded.modelspace().query('LWPOLYLINE')[0]
            points=list(p.get_points());points[0]=tuple([points[0][0]+1e-12,*points[0][1:]])
            p.set_points(points);rounded.saveas(root/'rounded.dxf')
            self.assertTrue(verify_dxf(original,root/'rounded.dxf')['geometry_layers_and_annotations_match'])
            for mutation in ('open','bulge','width','elevation','identity','self_intersection'):
                changed=ezdxf.readfile(original);p=changed.modelspace().query('LWPOLYLINE')[0]
                if mutation=='open':p.closed=False
                if mutation=='bulge':p.set_points([(0,0,0,0,.2),(2,0,0,0,0),(2,1,0,0,0),(0,1,0,0,0)])
                if mutation=='width':p.dxf.const_width=.01
                if mutation=='elevation':p.dxf.elevation=.1
                if mutation=='identity':p.discard_xdata('BSA_IFC')
                if mutation=='self_intersection':p.set_points([(0,0),(2,1),(2,0),(0,1)],format='xy')
                with self.subTest(mutation=mutation),self.assertRaises(ProjectError):validate_contours(changed)
                target=root/'changed.dxf';changed.saveas(target)
                with self.assertRaises(ProjectError):verify_dxf(original,target)

    def test_explicit_sheet_contract(self):
        for update in ({'scale_denominator':0},{'pdf_tolerance_mm':True},
                       {'reference_ifc_guid':''},{'window_drawing_units':[0,0,100,100]}):
            settings=json.loads(SETTINGS.read_text());settings.update(update)
            with self.assertRaises(ProjectError):validate_settings(settings)

    def test_reconciliation_detects_lost_ifc_identity_extra_entities_and_geometry_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'export.dxf';shutil.copyfile(SOURCE,path)
            self.assertTrue(verify_dxf(SOURCE,path)['model_entities_and_ifc_xdata_match'])
            for action in ('xdata','extra','geometry'):
                doc=ezdxf.readfile(SOURCE);line=doc.modelspace().query('LINE[layer=="BSA_PIPE_AXIS"]')[0]
                if action=='xdata':line.discard_xdata('BSA_IFC')
                elif action=='extra':doc.modelspace().add_line((0,0),(1,1))
                else:line.dxf.end=(9,9,0)
                doc.saveas(path)
                with self.subTest(action=action),self.assertRaises(ProjectError):verify_dxf(SOURCE,path)

    def test_workflow_missing_engine_pending_and_source_integrity(self):
        from bsa.workflow import execute,verify,validate_plan
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copyfile(SOURCE,root/'segments.dxf');shutil.copyfile(SETTINGS,root/'sheet.json')
            brief=root/'brief.md';brief.write_text('Save native diagram with explicit sheet and IFC identity checks.\n')
            task=dict(id='native',kind='ifc_native',dxf='segments.dxf',settings='sheet.json')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[task],
                      requirements=[dict(id='R1',passage='P001',quote='Save native diagram with explicit sheet and IFC identity checks.',task='native',acceptance='Native reopen and physical PDF checks; visual review separate')])
            path=root/'plan.json';path.write_text(json.dumps(plan));result=execute(path,root/'run')
            self.assertEqual(result['tasks']['native']['status'],'pending')
            self.assertFalse((root/'run/native/segments.dwg').exists())
            self.assertTrue(verify(root/'run')['integrity_pass'])
            (root/'segments.dxf').write_bytes((root/'segments.dxf').read_bytes()+b'\n')
            self.assertFalse(verify(root/'run')['integrity_pass'])
            task.pop('dxf');task['depends_on']='native';path.write_text(json.dumps(plan))
            with self.assertRaises(ProjectError):validate_plan(path)

    def test_failed_drawing_producer_leaves_native_pending_without_starting_engine(self):
        from bsa.workflow import execute
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'broken.ifc').write_text('not an IFC file')
            (root/'projection.json').write_text(json.dumps(dict(projection_axes=['X','Z'],annotation_height_m=.12,source='negative test')))
            shutil.copyfile(SETTINGS,root/'sheet.json')
            brief=root/'brief.md';brief.write_text('Produce diagram and native output only when its producer passes.\n')
            tasks=[dict(id='drawing',kind='ifc_drawing',ifc='broken.ifc',settings='projection.json'),
                   dict(id='native',kind='ifc_native',depends_on='drawing',settings='sheet.json')]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=tasks,
                      requirements=[dict(id='R'+str(i),passage='P001',quote='Produce diagram and native output only when its producer passes.',task=t['id'],acceptance='Failed upstream blocks native output') for i,t in enumerate(tasks)])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            result=execute(path,root/'run',autocad=root/'does-not-exist.exe')
            self.assertEqual(result['tasks']['drawing']['status'],'fail')
            self.assertEqual(result['tasks']['native']['status'],'pending')
            self.assertFalse((root/'run/native').exists())

    def test_workflow_pins_used_engine_and_native_methods_without_starting_mock_engine(self):
        from bsa.workflow import execute,verify,validate_plan
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copyfile(SOURCE,root/'segments.dxf');shutil.copyfile(SETTINGS,root/'sheet.json')
            engine=root/'controlled-engine.exe';engine.write_bytes(b'controlled runtime identity, never executed')
            brief=root/'brief.md';brief.write_text('Create a native schematic with an explicit runtime.\n')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[dict(id='native',kind='ifc_native',dxf='segments.dxf',settings='sheet.json')],requirements=[dict(id='R1',passage='P001',quote='Create a native schematic with an explicit runtime.',task='native',acceptance='Runtime/source correspondence; this controlled test does not execute AutoCAD')])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            _,inputs=validate_plan(path)
            self.assertTrue(all(ROOT/'src/bsa'/name in inputs for name in ('ifc_native.py','native_cad.py','cad_intake.py','cad_overlay.py','cad_sheet.py')))
            with patch('bsa.ifc_native.run',return_value=dict(native_reopen_pass=True,plot=dict(pdf_reference_pass=True))) as native:
                result=execute(path,root/'run',autocad=engine)
            native.assert_called_once()
            self.assertEqual(result['runtime_inputs'][str(engine.resolve())],digest(engine))
            self.assertTrue(verify(root/'run')['integrity_pass'])
            engine.write_bytes(b'changed runtime identity')
            self.assertFalse(verify(root/'run')['integrity_pass'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_AUTOCAD')=='1' and DEFAULT_EXE.is_file(),'requires local AutoCAD')
    def test_actual_native_reopen_xdata_and_fixed_scale_pdf(self):
        before=digest(SOURCE)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            result=run(SOURCE,SETTINGS,Path(folder)/'native',DEFAULT_EXE)
            self.assertTrue(result['native_reopen_pass'])
            self.assertEqual(result['checks']['model_entity_count'],8)
            self.assertEqual(result['checks']['linked_entity_count'],6)
            self.assertAlmostEqual(result['plot']['reference_expected_mm'],50)
            self.assertAlmostEqual(result['plot']['reference_measured_mm'],50,delta=.2)
            self.assertEqual(result['plot']['visual_review'],'pending')
            self.assertFalse(result['design_accepted']);self.assertEqual(digest(SOURCE),before)


if __name__=='__main__':unittest.main()
