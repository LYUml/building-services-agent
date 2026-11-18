import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from ezdxf.enums import TextEntityAlignment
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase_bridge import run as study_run
from bsa.three_phase_drawing import run,native_records,bus_contacts,verify_contacts,APP
from bsa.cad_overlay import equivalent

ROOT=Path(__file__).resolve().parents[1]
DOT=os.environ.get('BSA_TEST_GRAPHVIZ')
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class NativeTextAnchorTests(unittest.TestCase):
    def test_circuit_crossing_an_undeclared_bus_is_rejected(self):
        doc = ezdxf.new()
        doc.appids.new(APP)
        for name, x in [('A', 0), ('B', 10), ('C', 5)]:
            entity = doc.modelspace().add_line((x, -1), (x, 1))
            entity.set_xdata(APP, [(1000, 'bus'), (1000, name)])
        feeder = doc.modelspace().add_line((0, 0), (10, 0))
        feeder.set_xdata(APP, [(1000, 'line'), (1000, 'feeder')])
        with self.assertRaisesRegex(ProjectError, 'line feeder touches undeclared bus C') as error:
            bus_contacts(doc, [{'id': 'feeder', 'from': 'A', 'to': 'B'}])
        self.assertIn(f'line handle {feeder.dxf.handle}, bus handle {entity.dxf.handle}', str(error.exception))
        entity.dxf.start += (0, 0, 1)
        entity.dxf.end += (0, 0, 1)
        with self.assertRaisesRegex(ProjectError, f'bus C has invalid planar geometry on handle {entity.dxf.handle}'):
            bus_contacts(doc, [{'id': 'feeder', 'from': 'A', 'to': 'B'}])

    def test_overlapping_bus_geometry_makes_contact_assignment_ambiguous(self):
        doc = ezdxf.new()
        doc.appids.new(APP)
        for kind, name in [('bus', 'A'), ('bus', 'B'), ('line', 'feeder')]:
            entity = doc.modelspace().add_line((0, 0), (1, 0))
            entity.set_xdata(APP, [(1000, kind), (1000, name)])

        with self.assertRaisesRegex(ProjectError, 'ambiguous contacts at buses A and B'):
            bus_contacts(doc, [{'id': 'feeder', 'from': 'A', 'to': 'B'}])

    def test_only_derived_text_insert_is_normalized(self):
        a=ezdxf.new();text=a.modelspace().add_text('source').set_placement((10,20),align=TextEntityAlignment.CENTER)
        expected=native_records(a)
        text.dxf.insert=(3,20,0)
        self.assertTrue(equivalent(expected,native_records(a)))
        text.dxf.align_point=(11,20,0)
        self.assertFalse(equivalent(expected,native_records(a)))
        text.dxf.align_point=(10,20,0);text.dxf.height*=2
        self.assertFalse(equivalent(expected,native_records(a)))


@unittest.skipUnless(DOT and PYTHON,'requires explicit Graphviz and isolated three-phase runtime')
class ThreePhaseDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.temp.name)
        shutil.copytree(ROOT/'examples/three-phase-network',cls.root/'source')
        cls.project=cls.root/'source/project.json';cls.study=cls.root/'study'
        study_run(cls.project,cls.study,Path(PYTHON))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_real_layout_dxf_identity_and_phase_schedules(self):
        out=self.root/'drawing';result=run(self.project,self.study,out,Path(DOT))
        self.assertTrue(result['dxf_identity_pass']);self.assertFalse(result['design_accepted'])
        doc=ezdxf.readfile(out/'schematic.dxf')
        self.assertEqual(verify_contacts(self.project, self.study, out/'schematic.dxf')['bus_contacts'],
                         result['dxf_bus_contacts'])
        tagged_line = next(iter(doc.modelspace().query('LINE[layer=="BSA_ELEC_LINE"]')))
        original_tags = list(tagged_line.get_xdata(APP))
        tagged_line.set_xdata(APP, [*original_tags[:2], (1000, '0' * 64)])
        wrong_study = out/'wrong-study.dxf'
        doc.saveas(wrong_study)
        with self.assertRaisesRegex(ProjectError, 'Drawing study identity differs on handle'):
            verify_contacts(self.project, self.study, wrong_study)
        tagged_line.set_xdata(APP, original_tags)
        label = next(entity for entity in doc.modelspace().query('TEXT') if entity.dxf.text.startswith('VA='))
        label_text = label.dxf.text
        label.dxf.text = 'VA=999.00 V'
        wrong_label = out/'wrong-voltage-label.dxf'
        doc.saveas(wrong_label)
        with self.assertRaisesRegex(ProjectError, 'Saved bus .* labels differ from the study'):
            verify_contacts(self.project, self.study, wrong_label)
        label.dxf.text = label_text
        alignment, anchor, _ = label.get_placement()
        label.set_placement(anchor + (100, 0, 0), align=alignment)
        moved_label = out/'moved-voltage-label.dxf'
        doc.saveas(moved_label)
        with self.assertRaisesRegex(ProjectError, f'label anchor lies outside its box on handle {label.dxf.handle}'):
            verify_contacts(self.project, self.study, moved_label)
        label.set_placement(anchor, align=alignment)
        incomplete = ezdxf.readfile(out/'schematic.dxf')
        edge = next(entity for entity in incomplete.modelspace().query('LINE[layer=="BSA_ELEC_BUS"]')
                    if entity.dxf.start.y == entity.dxf.end.y)
        bus = edge.get_xdata(APP)[1].value
        incomplete.modelspace().delete_entity(edge)
        missing_edge = out/'missing-bus-edge.dxf'
        incomplete.saveas(missing_edge)
        with self.assertRaisesRegex(ProjectError, f'Saved bus {bus} does not have a closed rectangular outline'):
            verify_contacts(self.project, self.study, missing_edge)
        circuits = json.loads(self.project.read_text(encoding='utf-8-sig'))['lines']
        self.assertEqual(len(bus_contacts(doc, circuits)), 2)
        self.assertEqual(result['dxf_bus_contacts'], bus_contacts(doc, circuits))
        feeder = next(entity for entity in doc.modelspace().query('LINE')
                      if [tag.value for tag in entity.get_xdata(APP)[:2]] == ['line', 'feeder'])
        feeder.dxf.start += (1, 0, 0)
        with self.assertRaisesRegex(ProjectError, 'Saved line feeder does not meet'):
            bus_contacts(doc, circuits)
        feeder.dxf.start -= (1, 0, 0)
        loop = [(5, 5), (6, 5), (6, 6)]
        for start, end in zip(loop, loop[1:] + loop[:1]):
            extra = doc.modelspace().add_line(start, end)
            extra.set_xdata(APP, feeder.get_xdata(APP))
        with self.assertRaisesRegex(ProjectError, 'Saved line feeder contains disconnected geometry'):
            bus_contacts(doc, circuits)
        for extra in list(doc.modelspace().query('LINE[layer=="0"]')):
            doc.modelspace().delete_entity(extra)
        identities=[[(t.code,t.value) for t in e.get_xdata(APP)] for e in doc.modelspace()]
        self.assertTrue(any((1000,'feeder') in tags for tags in identities))
        text=[e.dxf.text for e in doc.modelspace().query('TEXT')]
        self.assertIn('L=40.00 m',text);self.assertIn('L=25.00 m',text)
        self.assertTrue(any('Not an installation drawing' in t for t in text))
        with (out/'loads.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),6);self.assertEqual(float(rows[2]['reactive_kvar']),-0.2)
        with (out/'lines.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),6);self.assertEqual(float(rows[0]['source_route_length_m']),40)
        self.assertEqual(result['artifacts']['schematic.dxf'],digest(out/'schematic.dxf'))

    def test_modified_study_or_failed_target_cannot_generate_drawing(self):
        altered=self.root/'altered';shutil.copytree(self.study,altered)
        f=altered/'native/study.json';f.write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'artifacts changed'):run(self.project,altered,self.root/'bad-study',Path(DOT))
        self.assertFalse((self.root/'bad-study').exists())
        failed=self.root/'failed';shutil.copytree(self.study,failed)
        f=failed/'native/study.json';data=json.loads(f.read_text());data.update(status='fail',study_targets_pass=False)
        f.write_text(json.dumps(data),encoding='utf-8')
        summary=failed/'three-phase.json';data=json.loads(summary.read_text());data.update(status='fail',study_sha256=digest(f))
        summary.write_text(json.dumps(data),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'passing numerical'):run(self.project,failed,self.root/'bad-target',Path(DOT))
        self.assertFalse((self.root/'bad-target').exists())

    def test_layout_endpoint_swap_is_rejected(self):
        original=subprocess.run
        def swapped(*args,**kwargs):
            result=original(*args,**kwargs);data=json.loads(result.stdout)
            data['edges'][0]['tail']=data['edges'][0]['head']
            result.stdout=json.dumps(data).encode();return result
        with patch('bsa.three_phase_drawing.subprocess.run',side_effect=swapped):
            with self.assertRaisesRegex(ProjectError,'endpoint identity'):run(self.project,self.study,self.root/'wrong-layout',Path(DOT))
        self.assertFalse((self.root/'wrong-layout/schematic.dxf').exists())

    def test_bus_label_relocated_outside_its_box_is_rejected(self):
        original = subprocess.run

        def displaced(*args, **kwargs):
            result = original(*args, **kwargs)
            layout = json.loads(result.stdout)
            bus, other_bus = layout['objects'][:2]
            label = next(op for op in bus['_ldraw_'] if op['op'] == 'T')
            label['pt'] = next(op['pt'] for op in other_bus['_ldraw_'] if op['op'] == 'T')
            result.stdout = json.dumps(layout).encode()
            return result

        output = self.root/'displaced-label'
        with patch('bsa.three_phase_drawing.subprocess.run', side_effect=displaced):
            with self.assertRaisesRegex(ProjectError, 'label anchor lies outside its box'):
                run(self.project, self.study, output, Path(DOT))
        self.assertFalse((output/'schematic.dxf').exists())

    def test_line_with_correct_ids_but_displaced_endpoint_is_rejected(self):
        original = subprocess.run

        def displaced(*args, **kwargs):
            result = original(*args, **kwargs)
            layout = json.loads(result.stdout)
            spline = next(op for op in layout['edges'][0]['_draw_'] if op['op'] == 'b')
            spline['points'][0][0] += 5
            result.stdout = json.dumps(layout).encode()
            return result

        output = self.root/'displaced-end'
        with patch('bsa.three_phase_drawing.subprocess.run', side_effect=displaced):
            with self.assertRaisesRegex(ProjectError, 'Line feeder does not meet bus source'):
                run(self.project, self.study, output, Path(DOT))
        self.assertFalse((output/'schematic.dxf').exists())


if __name__=='__main__':unittest.main()
