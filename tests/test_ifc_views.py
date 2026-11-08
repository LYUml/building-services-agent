import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import ezdxf
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_views import run,run_native,validate_settings,verify_manifest
from bsa.native_cad import DEFAULT_EXE

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/evidence/water-ifc/run/water/model.ifc'
SETTINGS=ROOT/'examples/water-loop-ifc/views-settings.json'


class ViewSettingsTests(unittest.TestCase):
    def test_explicit_distinct_planes_symbols_callouts_and_print_contract(self):
        for change in (lambda p:p.update(end_on_marker_half_size_m=0),
                       lambda p:p['views'][1].update(projection_axes=['Y','X']),
                       lambda p:p['views'][0].update(id='../escape'),
                       lambda p:p['views'][0]['sheet'].update(window_drawing_units=[0,0,100,100]),
                       lambda p:p['labels'].update({next(iter(p['labels'])):'unsafe label\n'})):
            p=json.loads(SETTINGS.read_text());change(p)
            with self.assertRaises(ProjectError):validate_settings(p)


@unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'requires IFC runtime')
class IFCViewsTests(unittest.TestCase):
    def fixture(self):
        folder=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(folder.cleanup)
        root=Path(folder.name);run(SOURCE,SETTINGS,root/'views');return root,root/'views/views.json'

    def test_all_three_views_cover_every_pipe_with_correct_end_on_lengths(self):
        original=digest(SOURCE);root,manifest=self.fixture();p=verify_manifest(manifest)
        self.assertTrue(p['calculated_checks_pass']);self.assertFalse(p['design_accepted'])
        self.assertEqual(len(p['views']),3);self.assertEqual(len(p['axis_coverage']),6)
        self.assertTrue(all(len(v)==2 for v in p['axis_coverage'].values()))
        for view in p['views']:
            self.assertEqual(sum(r['mode']=='axis' for r in view['segments']),4)
            self.assertEqual(sum(r['mode']=='end_on' for r in view['segments']),2)
            doc=ezdxf.readfile(manifest.parent/view['dxf'])
            self.assertEqual(len(doc.modelspace().query('LINE[layer=="BSA_END_ON"]')),4)
            self.assertTrue(all(r['projected_length_m']==0 for r in view['segments'] if r['mode']=='end_on'))
        plan=p['views'][0];vertical=[r for r in plan['segments'] if r['mode']=='end_on']
        self.assertTrue(all(r['true_length_m']==2 for r in vertical))
        self.assertEqual(digest(SOURCE),original)
        with self.assertRaises(FileExistsError):run(SOURCE,SETTINGS,manifest.parent)

    def test_updated_file_hash_cannot_hide_wrong_projection_or_missing_symbol(self):
        for action in ('axis','symbol','label','metadata','escape'):
            with self.subTest(action=action):
                root,manifest=self.fixture();p=json.loads(manifest.read_text());view=p['views'][0]
                if action in ('axis','symbol','label'):
                    file=manifest.parent/view['dxf'];doc=ezdxf.readfile(file)
                    entity=doc.modelspace().query('LINE[layer=="BSA_PIPE_AXIS"]')[0] if action=='axis' else doc.modelspace().query('LINE[layer=="BSA_END_ON"]')[0]
                    if action=='axis':entity.dxf.end=(99,99,0)
                    elif action=='symbol':doc.modelspace().delete_entity(entity)
                    else:
                        for record in view['segments']:
                            doc.entitydb[record['handles'][-1]].dxf.insert=(99,99,0)
                            doc.entitydb[record['handles'][-2]].dxf.end=(98,99,0)
                    doc.saveas(file);p['artifacts'][view['dxf']]=digest(file)
                elif action=='metadata':view['segments'][0]['true_length_m']+=1
                else:p['artifacts']['../outside.json']='0'*64
                manifest.write_text(json.dumps(p))
                with self.assertRaises(ProjectError):verify_manifest(manifest)
                with self.assertRaises(ProjectError):run_native(manifest,root/'native',DEFAULT_EXE)
                self.assertFalse((root/'native').exists())

    def test_end_on_print_reference_and_clipped_window_rejected(self):
        p=json.loads(SETTINGS.read_text());p['views'][0]['sheet']['reference_ifc_guid']=next(g for g,label in p['labels'].items() if label=='AC0')
        with tempfile.TemporaryDirectory() as f:
            root=Path(f);settings=root/'settings.json';settings.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError,'nonzero projected axis'):run(SOURCE,settings,root/'end-on-reference')
            p=json.loads(SETTINGS.read_text());p['views'][0]['sheet']['window_drawing_units']=[0,0,1,1];settings.write_text(json.dumps(p))
            with self.assertRaisesRegex(ProjectError,'outside declared sheet window'):run(SOURCE,settings,root/'clipped')

    def test_workflow_preserves_missing_native_engine_as_pending(self):
        from bsa.workflow import execute,verify
        with tempfile.TemporaryDirectory() as f:
            root=Path(f);shutil.copyfile(SOURCE,root/'model.ifc');shutil.copyfile(SETTINGS,root/'settings.json')
            brief=root/'brief.md';brief.write_text('Create complete multiview pipe diagrams and native plotted sheets.\n')
            tasks=[dict(id='views',kind='ifc_views',ifc='model.ifc',settings='settings.json'),dict(id='native',kind='ifc_views_native',depends_on='views')]
            plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={'P001':'requirement'},tasks=tasks,
                      requirements=[dict(id='R'+str(i),passage='P001',quote='Create complete multiview pipe diagrams and native plotted sheets.',task=t['id'],acceptance='Scoped diagrams/native proof; visual acceptance separate') for i,t in enumerate(tasks)])
            path=root/'plan.json';path.write_text(json.dumps(plan));r=execute(path,root/'run')
            self.assertEqual(r['tasks']['views']['status'],'pass');self.assertEqual(r['tasks']['native']['status'],'pending')
            self.assertFalse((root/'run/native').exists());self.assertTrue(verify(root/'run')['integrity_pass'])

    @unittest.skipUnless(os.environ.get('BSA_TEST_AUTOCAD')=='1' and DEFAULT_EXE.is_file(),'requires AutoCAD')
    def test_actual_three_native_reopens_and_merged_pdf_references(self):
        from pypdf import PdfReader
        root,manifest=self.fixture();r=run_native(manifest,root/'native',DEFAULT_EXE)
        self.assertTrue(r['calculated_checks_pass']);self.assertTrue(r['merged_page_content_match'])
        self.assertFalse(r['design_accepted']);self.assertEqual(len(PdfReader(root/'native/drawing-set.pdf').pages),3)
        for view in r['views']:
            self.assertTrue(view['native']['checks']['model_entities_and_ifc_xdata_match'])
            self.assertAlmostEqual(view['native']['plot']['reference_expected_mm'],100)
            self.assertAlmostEqual(view['native']['plot']['reference_measured_mm'],100,delta=.2)
            self.assertEqual(view['native']['plot']['visual_review'],'pending')
