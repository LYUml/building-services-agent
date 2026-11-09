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
from bsa.three_phase_drawing import run,native_records,APP
from bsa.cad_overlay import equivalent

ROOT=Path(__file__).resolve().parents[1]
DOT=os.environ.get('BSA_TEST_GRAPHVIZ')
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class NativeTextAnchorTests(unittest.TestCase):
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


if __name__=='__main__':unittest.main()
