import copy
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase import prepare
from bsa.three_phase_ifc import inspect
from bsa.three_phase_ifc_project import run

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class ModelDrivenProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'examples/three-phase-network',self.root/'source')
        self.project=self.root/'source/project.json'
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(self.project,self.root/'source/cable-geometry.json',self.root/'fixture','extrusion')
        self.ifc=self.root/'fixture/cables.ifc';self.binding=self.root/'fixture/binding.json'
        baseline=json.loads(self.project.read_text())
        for line in baseline['lines']:line['length_m']*=2
        basis=self.project.parent/'basis.md'
        with basis.open('a',encoding='utf-8') as f:f.write('\nDeliberately stale comparison lengths: feeder 80 m, branch 50 m. Software test only.\n')
        for value in baseline['sources'].values():value['sha256']=digest(basis)
        self.project.write_text(json.dumps(baseline),encoding='utf-8')

    def derive(self,python=None):return run(self.project,self.ifc,self.binding,self.root/'derived',python)

    def test_only_lengths_and_length_provenance_change(self):
        before=digest(self.project);old,_=prepare(self.project)
        report=self.derive();new,_=prepare(self.root/'derived/project.json')
        self.assertEqual(digest(self.project),before)
        self.assertEqual(report['changes'],[dict(id='feeder',baseline_length_m=80,derived_length_m=40.),dict(id='branch',baseline_length_m=50,derived_length_m=25.)])
        self.assertEqual(new['loads'],old['loads']);self.assertEqual(new['supply'],old['supply'])
        for a,b in zip(old['lines'],new['lines']):
            c=copy.deepcopy(b);c.pop('length_source');c['length_m']=a['length_m'];self.assertEqual(a,c)
        self.assertEqual(new['sources']['ifc_route_lengths']['kind'],'assumption')
        self.assertTrue(report['derived_geometry_correspondence_pass'])
        self.assertFalse(report['design_accepted'])

    def test_extraction_does_not_claim_old_length_correspondence(self):
        observed=inspect(self.project,self.ifc,self.binding,require_length_match=False)
        self.assertTrue(observed['native_geometry_checks_pass'])
        self.assertFalse(observed['geometry_correspondence_pass'])
        with self.assertRaisesRegex(ProjectError,'route length differs'):inspect(self.project,self.ifc,self.binding)

    def test_saved_model_tamper_invalidates_derived_project(self):
        self.derive()
        with (self.root/'derived/model/cables.ifc').open('a') as f:f.write('\n')
        with self.assertRaisesRegex(ProjectError,'source path/hash'):prepare(self.root/'derived/project.json')

    def test_repeated_derivation_retains_old_source_records(self):
        self.derive();first=self.root/'derived'
        run(first/'project.json',first/'model/cables.ifc',first/'model/binding.json',self.root/'revision')
        p,_=prepare(self.root/'revision/project.json')
        self.assertIn('ifc_route_lengths',p['sources'])
        self.assertIn('ifc_route_lengths_2',p['sources'])
        self.assertTrue(all(l['length_source']=='ifc_route_lengths_2' for l in p['lines']))

    def test_missing_length_source_and_overwrite_rejected(self):
        self.derive();path=self.root/'derived/project.json';p=json.loads(path.read_text())
        p['lines'][0]['length_source']='missing';path.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'unknown source'):prepare(path)
        with self.assertRaisesRegex(ProjectError,'new separate'):self.derive()

    @unittest.skipUnless(PYTHON,'requires explicit isolated numerical runtime')
    def test_actual_recalculation_uses_native_lengths_and_changes_voltages(self):
        from bsa.three_phase_bridge import run as solve
        solve(self.project,self.root/'baseline-study',Path(PYTHON))
        report=self.derive(Path(PYTHON))
        self.assertEqual(report['numerical_status'],'pass')
        old=json.loads((self.root/'baseline-study/native/study.json').read_text())
        new=json.loads((self.root/'derived/study/native/study.json').read_text())
        self.assertNotEqual(old['nodes'],new['nodes'])
        self.assertNotEqual(old['network_sha256'],new['network_sha256'])

    @unittest.skipUnless(PYTHON,'requires explicit isolated numerical runtime')
    def test_derivation_does_not_clear_failed_current_targets(self):
        p=json.loads(self.project.read_text())
        for line in p['lines']:line['max_current_a']=1
        self.project.write_text(json.dumps(p),encoding='utf-8')
        report=self.derive(Path(PYTHON))
        self.assertEqual(report['numerical_status'],'fail')
        self.assertFalse(report['design_accepted'])
