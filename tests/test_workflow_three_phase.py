import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute
from bsa.workflow_status import diagnose
from bsa import three_phase_bridge

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class ThreePhaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'examples/three-phase-network',self.root/'source')
        self.plan=self.root/'source/plan.json'

    def test_missing_runtime_keeps_study_and_release_pending(self):
        with patch.object(three_phase_bridge,'run') as runner:
            result=execute(self.plan,self.root/'run')
        runner.assert_not_called()
        self.assertEqual(result['tasks']['power-flow']['status'],'pending')
        self.assertFalse((self.root/'run/power-flow').exists())
        rows={r['id']:r for r in diagnose(self.plan,self.root/'run')['tasks']}
        self.assertEqual(rows['review']['blocked_by'],['power-flow'])
        self.assertIn(str((self.root/'source/basis.md').resolve()),result['inputs'])

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_actual_pass_and_converged_overload_gate(self):
        result=execute(self.plan,self.root/'pass',three_phase_python=Path(PYTHON))
        self.assertEqual(result['tasks']['power-flow']['status'],'pass')
        self.assertEqual(diagnose(self.plan,self.root/'pass')['tasks'][1]['blocked_by'],[])
        basis=self.root/'source/basis.md';basis.write_text(basis.read_text(encoding='utf-8').replace('100 A','1 A'),encoding='utf-8')
        project=self.root/'source/project.json';p=json.loads(project.read_text(encoding='utf-8-sig'))
        for line in p['lines']:line['max_current_a']=1
        for source in p['sources'].values():source['sha256']=digest(basis)
        project.write_text(json.dumps(p),encoding='utf-8')
        result=execute(self.plan,self.root/'fail',three_phase_python=Path(PYTHON))
        self.assertEqual(result['tasks']['power-flow']['status'],'fail')
        native=json.loads((self.root/'fail/power-flow/native/study.json').read_text())
        self.assertTrue(native['verification_pass']);self.assertFalse(native['study_targets_pass'])
        self.assertEqual(diagnose(self.plan,self.root/'fail')['tasks'][1]['blocked_by'],['power-flow'])

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_exit_zero_without_study_is_failure(self):
        with patch.object(three_phase_bridge.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
            with self.assertRaisesRegex(ProjectError,'no verified study'):
                three_phase_bridge.run(self.root/'source/project.json',self.root/'bad',Path(PYTHON))
        self.assertFalse((self.root/'bad/three-phase.json').exists())

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_incomplete_or_contradictory_child_report_is_rejected(self):
        original=subprocess.run
        mutations=[lambda s:s.update(verification_checks={}),
                   lambda s:s['residuals'].update(max_node_kcl_error_a=1),
                   lambda s:s['lines'][0].update(phase_current_a=[1000,1000,1000]),
                   lambda s:s.update(inputs={}),
                   lambda s:s['versions'].update(pandapower='unverified')]
        for i,change in enumerate(mutations):
            out=self.root/str(i)
            def altered(args,**kwargs):
                proc=original(args,**kwargs)
                f=out/'native/study.json';data=json.loads(f.read_text());change(data)
                f.write_text(json.dumps(data),encoding='utf-8')
                return proc
            with self.subTest(case=i),patch.object(three_phase_bridge.subprocess,'run',side_effect=altered):
                with self.assertRaises(ProjectError):three_phase_bridge.run(self.root/'source/project.json',out,Path(PYTHON))
            self.assertFalse((out/'three-phase.json').exists())


if __name__=='__main__':unittest.main()
