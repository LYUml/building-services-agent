import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import ezdxf
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.ifc_route_drawing import extract, run
from bsa.ifc_native import verify_dxf, run as native_run
from bsa.native_cad import DEFAULT_EXE

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('ifcopenshell'), 'requires IFC runtime')
class RouteDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'runs').mkdir(exist_ok=True)
        cls.folder = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        cls.root = Path(cls.folder.name)
        cls.ifc = cls.root/'route.ifc'
        with zipfile.ZipFile(ROOT/'docs/evidence/circular-elbow/workflow.zip') as z:
            cls.ifc.write_bytes(z.read('model/bim/model.ifc'))
        cls.model_path = ROOT/'examples/circular-elbow/project.json'
        cls.settings_path = ROOT/'examples/circular-elbow/drawing-settings.json'
        cls.sheet_path = ROOT/'examples/circular-elbow/native-sheet.json'
        cls.model = json.loads(cls.model_path.read_text())
        cls.settings = json.loads(cls.settings_path.read_text())
        cls.before = digest(cls.ifc)
        cls.result = run(cls.ifc, cls.model_path, cls.settings_path, cls.root/'drawing')
        cls.dxf = cls.root/'drawing/segments.dxf'

    @classmethod
    def tearDownClass(cls):
        assert digest(cls.ifc) == cls.before
        cls.folder.cleanup()

    def test_complete_identity_true_arc_od_outlines_and_schedule(self):
        self.assertEqual(self.result['piece_count'], 3)
        self.assertTrue(self.result['inputs_unchanged'])
        bend = next(r for r in self.result['pieces'] if r['name'] == 'BEND')
        self.assertAlmostEqual(bend['length_m'], math.pi*.3/2)
        self.assertTrue(bend['native_wall_checks']['through_bore_pass'])
        doc = ezdxf.readfile(self.dxf)
        axes = doc.modelspace().query('*[layer=="BSA_PIPE_AXIS"]')
        self.assertEqual(sorted(e.dxftype() for e in axes), ['ARC','LINE','LINE'])
        arc = next(e for e in axes if e.dxftype() == 'ARC')
        self.assertEqual(tuple(arc.dxf.center), (2,2,0))
        self.assertAlmostEqual(arc.dxf.radius, .3)
        self.assertAlmostEqual((arc.dxf.end_angle-arc.dxf.start_angle)%360, 90)
        self.assertEqual(arc.get_xdata('BSA_IFC')[0].value, bend['guid'])
        self.assertEqual(sorted(round(e.dxf.radius, 9) for e in doc.modelspace().query('ARC')), [.25,.3,.35])
        self.assertGreaterEqual(len(doc.modelspace()), 20)
        self.assertTrue(self.result['annotation_layout']['saved_leader_paths_match'])
        self.assertIn('BEND', (self.root/'drawing/segments.csv').read_text())
        self.assertFalse(self.result['design_accepted'])

    def test_reversed_plane_axes_preserve_arc_and_wrong_plane_rejected(self):
        settings = copy.deepcopy(self.settings);settings['projection_axes'] = ['Y','X']
        rows = extract(self.ifc, self.model, settings)
        bend = next(r for r in rows if r['name'] == 'BEND')
        self.assertAlmostEqual((bend['end_angle_deg']-bend['start_angle_deg'])%360,90)
        settings['projection_axes'] = ['X','Z']
        with self.assertRaisesRegex(ProjectError, 'drawing plane'):
            extract(self.ifc, self.model, settings)

    def test_body_axis_units_and_coverage_tampering_rejected(self):
        import ifcopenshell
        import ifcopenshell.api as api
        for action in ('body','axis','units','coverage'):
            native = ifcopenshell.open(str(self.ifc))
            obj = native.by_type('IfcPipeFitting')[0]
            if action in ('body','axis'):
                identifier = 'Body' if action == 'body' else 'Axis'
                rep = next(r for r in obj.Representation.Representations if r.RepresentationIdentifier == identifier)
                coords = rep.Items[0].Coordinates if action == 'body' else rep.Items[0].Points
                points = [list(p) for p in coords.CoordList];points[0][0] += .01
                coords.CoordList = points
            elif action == 'units':
                next(u for u in native.by_type('IfcSIUnit') if u.UnitType == 'LENGTHUNIT').Prefix = 'MILLI'
            else:
                api.run('root.create_entity',native,ifc_class='IfcSensor',name='UNCLAIMED')
            path = self.root/(action+'.ifc');native.write(str(path))
            with self.subTest(action=action), self.assertRaises(ProjectError):
                extract(path, self.model, self.settings)

    def test_native_reconciliation_rejects_arc_or_guid_change(self):
        for action in ('radius','angle','guid'):
            doc = ezdxf.readfile(self.dxf)
            arc = doc.modelspace().query('ARC[layer=="BSA_PIPE_AXIS"]')[0]
            if action == 'radius': arc.dxf.radius = .31
            elif action == 'angle': arc.dxf.end_angle = 180
            else: arc.set_xdata('BSA_IFC', [(1000,'wrong')])
            target = self.root/(action+'.dxf');doc.saveas(target)
            with self.subTest(action=action), self.assertRaises(ProjectError):
                verify_dxf(self.dxf, target)

    def test_axially_shifted_wall_with_unchanged_ports_rejected(self):
        import ifcopenshell
        import ifcopenshell.util.placement as placement
        native = ifcopenshell.open(str(self.ifc))
        before = {p.GlobalId:placement.get_local_placement(p.ObjectPlacement).tolist() for p in native.by_type('IfcDistributionPort')}
        obj = next(o for o in native.by_type('IfcPipeSegment') if o.Name == 'IN')
        solid = next(r for r in obj.Representation.Representations if r.RepresentationIdentifier == 'Body').Items[0]
        coords = list(solid.Position.Location.Coordinates);coords[2] += .02
        solid.Position.Location.Coordinates = coords
        path = self.root/'axial-shift.ifc';native.write(str(path))
        after = {p.GlobalId:placement.get_local_placement(p.ObjectPlacement).tolist() for p in native.by_type('IfcDistributionPort')}
        self.assertEqual(before,after)
        with self.assertRaisesRegex(ProjectError,'wall world bounds'):
            extract(path,self.model,self.settings)

    def test_clipped_annotation_or_nonplanar_arc_rejected_before_native_writes(self):
        settings = json.loads(self.sheet_path.read_text())
        settings['window_drawing_units'][2] = 3.5
        path = self.root/'clipped.json';path.write_text(json.dumps(settings))
        with patch('bsa.ifc_native.execute',side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(ProjectError, 'extents'):
                native_run(self.dxf,path,self.root/'clipped-native',Path(sys.executable))
            doc = ezdxf.readfile(self.dxf)
            doc.modelspace().query('ARC')[0].dxf.extrusion = (1,0,0)
            bad = self.root/'nonplanar.dxf';doc.saveas(bad)
            with self.assertRaisesRegex(ProjectError, 'WCS XY arc'):
                native_run(bad,self.sheet_path,self.root/'bad-native',Path(sys.executable))
        self.assertFalse((self.root/'clipped-native').exists())
        self.assertFalse((self.root/'bad-native').exists())

    @unittest.skipUnless(os.environ.get('BSA_TEST_AUTOCAD') == '1' and DEFAULT_EXE.is_file(), 'requires local AutoCAD')
    def test_actual_native_arc_reopen_identity_and_physical_pdf_scale(self):
        result = native_run(self.dxf,self.sheet_path,self.root/'native',DEFAULT_EXE)
        self.assertTrue(result['native_reopen_pass'])
        source = ezdxf.readfile(self.dxf)
        self.assertEqual(result['checks']['model_entity_count'],len(source.modelspace()))
        self.assertEqual(result['checks']['linked_entity_count'],sum(e.has_xdata('BSA_IFC') for e in source.modelspace()))
        self.assertAlmostEqual(result['plot']['reference_expected_mm'],60)
        self.assertAlmostEqual(result['plot']['reference_measured_mm'],60,delta=.2)
        self.assertEqual(result['plot']['visual_review'],'pending')

    def test_failed_route_drawing_blocks_native_workflow(self):
        from bsa.workflow import execute, verify
        root = self.root/'failed-workflow';root.mkdir()
        (root/'bad.ifc').write_text('not IFC')
        (root/'model.json').write_bytes(self.model_path.read_bytes())
        (root/'projection.json').write_bytes(self.settings_path.read_bytes())
        (root/'sheet.json').write_bytes(self.sheet_path.read_bytes())
        text = 'Draw the complete source-checked route and deliver native output only after successful extraction.'
        (root/'brief.md').write_text(text+'\n')
        tasks = [dict(id='drawing',kind='ifc_route_drawing',ifc='bad.ifc',model='model.json',settings='projection.json'),
                 dict(id='native',kind='ifc_native',depends_on='drawing',settings='sheet.json')]
        plan = dict(version=1,brief='brief.md',brief_sha256=digest(root/'brief.md'),passage_dispositions={'P001':'requirement'},tasks=tasks,
                    requirements=[dict(id='R'+str(i),passage='P001',quote=text,task=t['id'],acceptance='Failed producer blocks downstream native execution') for i,t in enumerate(tasks)])
        path = root/'plan.json';path.write_text(json.dumps(plan))
        result = execute(path,root/'run',autocad=root/'missing.exe')
        self.assertEqual(result['tasks']['drawing']['status'],'fail')
        self.assertEqual(result['tasks']['native']['status'],'pending')
        self.assertFalse((root/'run/native').exists())
        self.assertTrue(verify(root/'run')['integrity_pass'])
        self.assertIn(str((root/'model.json').resolve()),result['inputs'])


if __name__ == '__main__':unittest.main()
