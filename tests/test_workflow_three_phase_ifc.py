import copy
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch
import ifcopenshell
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow import execute,validate_plan,three_phase_rule_bindings

ROOT=Path(__file__).resolve().parents[1]
PYTHON=os.environ.get('BSA_TEST_THREE_PHASE_PYTHON')


class CableWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'examples/three-phase-network',self.root/'source')
        self.source=self.root/'source'
        author=runpy.run_path(str(ROOT/'scripts/author_three_phase_ifc_fixture.py'))['run']
        author(self.source/'project.json',self.source/'cable-geometry.json',self.source/'fixture','extrusion')
        passages=['Execute the synthetic three-phase numerical study.',
                  'Check saved straight cable geometry against the same study project.',
                  'Generate the calculation schematic only after saved geometry passes.',
                  'Review all installation and regulatory requirements separately.']
        brief=self.source/'ifc-brief.md';brief.write_text('\n\n'.join(passages),encoding='utf-8')
        self.p=dict(version=1,brief=brief.name,brief_sha256=digest(brief),
                    passage_dispositions={f'P{i:03}':'requirement' for i in range(1,5)},
                    tasks=[dict(id='study',kind='three_phase',project='project.json'),
                           dict(id='geometry',kind='three_phase_ifc',depends_on='study',ifc='fixture/cables.ifc',binding='fixture/binding.json'),
                           dict(id='drawing',kind='three_phase_drawing',depends_on='study',requires_pass=['geometry']),
                           dict(id='review',kind='manual',requires_pass=['drawing'])],
                    requirements=[dict(id=f'R{i}',passage=f'P{i:03}',quote=text,task=task,acceptance=text)
                                  for i,(text,task) in enumerate(zip(passages,['study','geometry','drawing','review']),1)])
        self.plan=self.source/'ifc-plan.json';self.save()

    def save(self):self.plan.write_text(json.dumps(self.p),encoding='utf-8')

    def test_no_runtime_blocks_geometry(self):
        with patch('bsa.three_phase_ifc.run') as check:
            result=execute(self.plan,self.root/'run')
        check.assert_not_called()
        self.assertEqual(result['tasks']['geometry']['status'],'pending')
        self.assertFalse((self.root/'run/geometry').exists())

    def test_replacement_project_and_other_study_gate_rejected(self):
        self.p['tasks'][1]['project']='project.json';self.save()
        with self.assertRaisesRegex(ProjectError,'replacement project'):validate_plan(self.plan)
        tasks=copy.deepcopy(self.p['tasks']);tasks[1].pop('project')
        tasks.insert(2,dict(id='other',kind='three_phase',project='project.json'))
        tasks[3]['depends_on']='other'
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(tasks)
        tasks.insert(3,dict(id='proxy',kind='manual',requires_pass=['geometry']))
        tasks[4]['requires_pass']=['proxy']
        with self.assertRaisesRegex(ProjectError,'different study'):three_phase_rule_bindings(tasks)

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_actual_study_geometry_pass_and_delivery_remains_pending(self):
        result=execute(self.plan,self.root/'run',three_phase_python=Path(PYTHON))
        self.assertEqual(result['tasks']['study']['status'],'pass')
        self.assertEqual(result['tasks']['geometry']['status'],'pass')
        self.assertEqual(result['tasks']['drawing']['status'],'pending')
        self.assertFalse(result['design_accepted'])
        self.assertEqual(result['three_phase_source_bindings'],[dict(check='geometry',consumer='drawing',study_producer='study')])

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_changed_geometry_blocks_drawing(self):
        path=self.source/'fixture/cables.ifc';model=ifcopenshell.open(str(path))
        model.by_type('IfcExtrudedAreaSolid')[0].Depth+=1;model.write(str(path))
        binding=self.source/'fixture/binding.json';data=json.loads(binding.read_text());data['ifc_sha256']=digest(path)
        binding.write_text(json.dumps(data),encoding='utf-8')
        with patch('bsa.three_phase_drawing.run') as draw:
            result=execute(self.plan,self.root/'run',three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called()
        self.assertEqual(result['tasks']['geometry']['status'],'fail')
        self.assertEqual(result['tasks']['drawing']['status'],'pending')

    @unittest.skipUnless(PYTHON,'requires explicit isolated runtime')
    def test_changed_check_artifact_blocks_before_drawing(self):
        from bsa.input_issues import blockers
        out=self.root/'run'
        def alter(plan,task_id):
            if task_id=='drawing':(out/'geometry/ifc-electrical-check.json').write_text('{}',encoding='utf-8')
            return blockers(plan,task_id)
        with patch('bsa.input_issues.blockers',side_effect=alter),patch('bsa.three_phase_drawing.run') as draw:
            result=execute(self.plan,out,three_phase_python=Path(PYTHON),graphviz=Path('unused'),autocad=Path('unused'))
        draw.assert_not_called()
        self.assertEqual(result['tasks']['drawing']['status'],'fail')
        self.assertIn('artifacts changed',result['tasks']['drawing']['scope'])
