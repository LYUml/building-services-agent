import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import ezdxf
from bsa.cad_overlay import run,snapshot,reconcile,validate_settings
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.native_cad import DEFAULT_EXE
from test_cad_intake import fixture

ROOT=Path(__file__).resolve().parents[1]


def inputs(root):
    drawing,selection=fixture(root)
    project=json.loads((ROOT/'examples/office-electrical/project.json').read_text())
    project['name']='Synthetic devices on an existing millimetre L-shaped base'
    for d,x in zip(project['devices'],[1,3,5]):d['x_m']=x;d['y_m']=.4
    config=dict(source='Synthetic explicit shared-WCS identity mapping and schematic annotation choices',translation_m=[0,0],rotation_deg=0,
                symbol_radius_m=.12,text_height_m=.12,label_offset_m=[-.4,.4])
    paths=[]
    for name,data in (('project',project),('selection',selection),('settings',config)):
        path=root/(name+'.json');path.write_text(json.dumps(data));paths.append(path)
    return paths[0],drawing,paths[1],paths[2]


class CADOverlayTests(unittest.TestCase):
    def test_mm_base_preserved_three_devices_and_tamper_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);args=inputs(root);original=snapshot(ezdxf.readfile(args[1]));before=digest(args[1])
            result=run(*args,root/'run')
            self.assertTrue(result['base_entities_preserved']);self.assertEqual(result['device_count'],3)
            self.assertFalse(result['native_reopen_pass']);self.assertEqual(digest(args[1]),before)
            self.assertEqual(result['placements'][0]['centre_drawing_units'],[1000,400,0])
            output=root/'run/coordinated.dxf';doc=ezdxf.readfile(output)
            self.assertEqual(len(doc.modelspace().query('CIRCLE[layer=="BSA_DEVICES"]')),3)
            doc.modelspace().query('LINE')[0].dxf.end=(6001,-1000,0)
            doc.saveas(output)
            with self.assertRaises(ProjectError):reconcile(original,output)

    def test_explicit_rotation_and_annotation_scale(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);args=inputs(root);config=json.loads(args[3].read_text())
            config.update(rotation_deg=90,translation_m=[10,20]);args[3].write_text(json.dumps(config))
            result=run(*args,root/'run');pt=result['placements'][0]['centre_drawing_units']
            self.assertAlmostEqual(pt[0],9600);self.assertAlmostEqual(pt[1],21000)
            doc=ezdxf.readfile(root/'run/coordinated.dxf')
            self.assertEqual(doc.modelspace().query('CIRCLE')[0].dxf.radius,120)
            self.assertEqual(doc.modelspace().query('TEXT[layer=="BSA_LABELS"]')[0].dxf.height,120)

    def test_bad_settings_and_unsupported_base_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);args=inputs(root);settings=json.loads(args[3].read_text())
            for mutate in (lambda p:p.update(rotation_deg=float('nan')),lambda p:p.update(symbol_radius_m=0),lambda p:p.update(translation_m=[0])):
                candidate=copy.deepcopy(settings);mutate(candidate)
                with self.assertRaises(ProjectError):validate_settings(candidate)
            doc=ezdxf.readfile(args[1]);doc.modelspace().add_ellipse((0,0),major_axis=(1,0))
            with self.assertRaises(ProjectError):snapshot(doc)

    def test_workflow_input_tracking_and_missing_sheet_engine_pending(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);inputs(root)
            brief=root/'brief.md';brief.write_text('Preserve the base and add the selected devices.\n')
            task=dict(id='overlay',kind='base_overlay',project='project.json',drawing='base.dxf',selection='selection.json',settings='settings.json')
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=[task],
                requirements=[dict(id='R1',passage='P001',quote='Preserve the base and add the selected devices.',task='overlay',acceptance='geometry consistency only')])
            path=root/'plan.json';path.write_text(json.dumps(plan));report=execute(path,root/'run')
            self.assertEqual(report['tasks']['overlay']['status'],'pass')
            self.assertTrue(verify(root/'run')['integrity_pass'])
            for name in ('project.json','base.dxf','selection.json','settings.json'):self.assertIn(str((root/name).resolve()),report['inputs'])
            (root/'sheet.json').write_text('{}');task['sheet']='sheet.json';path.write_text(json.dumps(plan))
            pending=execute(path,root/'pending')
            self.assertEqual(pending['tasks']['overlay']['status'],'pending')
            self.assertFalse(pending['design_accepted'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_AUTOCAD')=='1' and DEFAULT_EXE.is_file(),'requires local AutoCAD')
    def test_actual_native_base_and_devices_reopen(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);args=inputs(root)
            selected=json.loads(args[2].read_text());sheet=root/'sheet.json'
            sheet.write_text(json.dumps(dict(source='Synthetic explicit fixed-scale test',window_drawing_units=[-1000,-2000,7000,5000],
                scale_denominator=50,reference_handle=selected['unit_check']['handle'],pdf_tolerance_mm=.2)))
            result=run(*args,root/'run',DEFAULT_EXE,sheet)
            self.assertTrue(result['native_reopen_pass']);self.assertFalse(result['design_accepted'])
            self.assertTrue((root/'run/coordinated.dwg').is_file())
            self.assertTrue(result['plot']['pdf_reference_pass'])
            self.assertAlmostEqual(result['plot']['reference_measured_mm'],120,delta=.2)
            self.assertEqual(result['plot']['visual_review'],'pending')


if __name__=='__main__':unittest.main()
