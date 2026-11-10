import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from bsa.cli import digest
from bsa.workflow import intake,validate_plan,execute,verify
from bsa.engine import ProjectError
from bsa.native_cad import DEFAULT_EXE
ROOT=Path(__file__).resolve().parents[1]

class ConceptSectionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        stage=runpy.run_path(str(ROOT/'scripts/run_public_massing.py'))['stage'];d=json.loads((ROOT/'benchmarks/mit-4401-2018/massing-decisions.json').read_text(encoding='utf-8'));source=stage(d,d['variants'][0])
        source['sources']['design']='Synthetic workflow geometry, no measured project or course acceptance'
        files=dict(model=source,layout=dict(source='Synthetic rectangle layout',window_wall_ratio=.4,layout='centered-equal-fraction'),facade=json.loads((ROOT/'benchmarks/mit-4401-2018/facade-decisions.json').read_text(encoding='utf-8')),sheet=json.loads((ROOT/'benchmarks/mit-4401-2018/section-decisions/compact.json').read_text(encoding='utf-8')))
        for name,row in files.items():(self.root/(name+'.json')).write_text(json.dumps(row),encoding='utf-8')
        brief=self.root/'brief.md';brief.write_text('Author the synthetic concept spaces.\n\nCreate source-bound facade geometry.\n\nProduce all-storey native section sheets with actual plot review pending.\n',encoding='utf-8')
        document=intake(brief,self.root/'intake.json');rows=document['passages'];self.assertEqual(len(rows),3)
        tasks=[dict(id='model',kind='bim',project='model.json',concept_layout='layout.json'),dict(id='facade',kind='concept_facade',depends_on='model',basis='facade.json'),dict(id='sections',kind='concept_section',depends_on='facade',basis='sheet.json')]
        self.data=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'requirement' for r in rows},tasks=tasks,requirements=[dict(id='R'+str(i),passage=r['id'],quote=r['text'],task=t['id'],acceptance='Scoped synthetic execution; full design and plot acceptance pending') for i,(r,t) in enumerate(zip(rows,tasks),1)])
        self.plan=self.root/'plan.json';self.plan.write_text(json.dumps(self.data),encoding='utf-8')

    def test_missing_autocad_does_not_create_DXF_only_native_pass(self):
        out=self.root/'missing';r=execute(self.plan,out)
        self.assertEqual(r['tasks']['facade']['status'],'pass')
        self.assertEqual(r['tasks']['sections']['status'],'pending')
        self.assertIn('AutoCAD executable not supplied',r['tasks']['sections']['scope'])
        self.assertFalse((out/'sections').exists());self.assertTrue(verify(out)['integrity_pass']);self.assertFalse(r['design_accepted'])

    def test_wrong_parent_replacement_fields_and_invalid_basis_reject(self):
        for mode in ('replacement','parent','basis'):
            row=copy.deepcopy(self.data)
            if mode=='replacement':row['tasks'][2]['ifc']='replacement.ifc'
            if mode=='parent':row['tasks'][2]['depends_on']='model'
            if mode=='basis':
                p=self.root/'sheet.json';b=json.loads(p.read_text(encoding='utf-8'));b['scale_denominator']=0;p.write_text(json.dumps(b),encoding='utf-8')
            self.plan.write_text(json.dumps(row),encoding='utf-8')
            with self.subTest(mode=mode),self.assertRaises(ProjectError):validate_plan(self.plan)

    def test_upstream_geometry_failure_blocks_section_folder(self):
        p=self.root/'model.json';r=json.loads(p.read_text(encoding='utf-8'));r['spaces'][0]['size_m'][0]=-1;p.write_text(json.dumps(r),encoding='utf-8')
        out=self.root/'bad-source';r=execute(self.plan,out)
        self.assertEqual(r['tasks']['model']['status'],'fail');self.assertEqual(r['tasks']['sections']['status'],'pending');self.assertFalse((out/'sections').exists())

    @unittest.skipUnless(DEFAULT_EXE.is_file(),'requires installed executable for runtime hashing; no CAD launch')
    def test_false_native_reopen_flag_cannot_release_section_task(self):
        with patch('bsa.concept_section.run',return_value=dict(native_reopen_pass=False,design_accepted=False)) as adapter:r=execute(self.plan,self.root/'false-native',autocad=DEFAULT_EXE)
        adapter.assert_called_once();args=adapter.call_args.args
        self.assertEqual(args[0],self.root/'false-native/facade/facade.ifc')
        self.assertEqual(args[1],self.root/'model.json');self.assertEqual(args[2],self.root/'layout.json')
        self.assertEqual(r['tasks']['sections']['status'],'fail');self.assertFalse(r['design_accepted'])
        self.assertIn(str(DEFAULT_EXE),r['runtime_inputs'])
