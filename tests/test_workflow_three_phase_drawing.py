import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,validate_plan
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class DrawingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);shutil.copytree(ROOT/'examples/three-phase-network',self.root/'source')
        self.plan=self.root/'source/drawing-plan.json'

    def test_missing_study_runtime_blocks_drawing_and_review(self):
        with patch('bsa.three_phase_drawing.run') as draw:
            result=execute(self.plan,self.root/'run')
        draw.assert_not_called()
        self.assertEqual(result['tasks']['drawing']['status'],'pending')
        self.assertFalse((self.root/'run/drawing').exists())
        rows={r['id']:r for r in diagnose(self.plan,self.root/'run')['tasks']}
        self.assertEqual(rows['drawing']['blocked_by'],['power-flow'])
        self.assertEqual(rows['review']['upstream_action_tasks'],['power-flow'])

    def test_replacement_project_or_invalid_producer_rejected(self):
        p=json.loads(self.plan.read_text(encoding='utf-8-sig'))
        p['tasks'][1]['project']='project.json';self.plan.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'replacement'):validate_plan(self.plan)
        del p['tasks'][1]['project'];p['tasks'][1]['depends_on']='review'
        self.plan.write_text(json.dumps(p),encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'earlier three_phase'):validate_plan(self.plan)

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_missing_graphviz_or_autocad_does_not_call_drawing(self):
        for name,engines,reason in [('graphviz',{},'Graphviz'),('autocad',{'graphviz':Path('not-executed.exe')},'AutoCAD')]:
            with self.subTest(name=name),patch('bsa.three_phase_drawing.run') as draw:
                result=execute(self.plan,self.root/name,three_phase_python=Path(PYTHON),**engines)
            draw.assert_not_called()
            self.assertEqual(result['tasks']['power-flow']['status'],'pass')
            self.assertIn(reason,result['tasks']['drawing']['scope'])
            self.assertFalse((self.root/name/'drawing').exists())

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_converged_failed_target_blocks_actual_drawing(self):
        basis=self.root/'source/basis.md';basis.write_text(basis.read_text(encoding='utf-8').replace('100 A','1 A'),encoding='utf-8')
        f=self.root/'source/project.json';p=json.loads(f.read_text(encoding='utf-8-sig'))
        for line in p['lines']:line['max_current_a']=1
        for source in p['sources'].values():source['sha256']=digest(basis)
        f.write_text(json.dumps(p),encoding='utf-8')
        with patch('bsa.three_phase_drawing.run') as draw:
            result=execute(self.plan,self.root/'failed',three_phase_python=Path(PYTHON),graphviz=Path('not-used.exe'),autocad=Path('not-used.exe'))
        draw.assert_not_called()
        self.assertEqual(result['tasks']['power-flow']['status'],'fail')
        self.assertEqual(result['tasks']['drawing']['status'],'pending')
        self.assertEqual(diagnose(self.plan,self.root/'failed')['tasks'][2]['upstream_action_tasks'],['power-flow'])

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_changed_producer_bytes_block_before_drawing_adapter(self):
        from bsa.input_issues import blockers
        out=self.root/'changed'
        def altered(plan,task_id):
            if task_id=='drawing':(out/'power-flow/native/study.json').write_text('{}',encoding='utf-8')
            return blockers(plan,task_id)
        with patch('bsa.input_issues.blockers',side_effect=altered),patch('bsa.three_phase_drawing.run') as draw:
            result=execute(self.plan,out,three_phase_python=Path(PYTHON),graphviz=Path('not-used.exe'),autocad=Path('not-used.exe'))
        draw.assert_not_called()
        self.assertEqual(result['tasks']['drawing']['status'],'fail')
        self.assertIn('producer artifacts changed',result['tasks']['drawing']['scope'])
        self.assertFalse((out/'drawing').exists())


if __name__=='__main__':unittest.main()
